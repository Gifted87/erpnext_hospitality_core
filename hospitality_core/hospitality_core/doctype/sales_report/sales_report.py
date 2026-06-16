# Copyright (c) 2026, Gift Braimah and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class SalesReport(Document):
    @frappe.whitelist()
    def generate_report(self):
        self.clear_existing_data()
        
        closing_entries = self.get_closing_entries()
        if not closing_entries:
            frappe.msgprint("No POS Closing Entries found for the selected criteria.")
            return
            
        closing_entry_names = tuple([e.name for e in closing_entries])
        
        self.aggregate_kpis(closing_entries)
        self.aggregate_invoices(closing_entry_names)
        self.aggregate_payments(closing_entry_names)
        self.flag_discrepancies(closing_entries)
        
        # Extract Cashiers Full Names
        unique_users = list({e.user for e in closing_entries if e.get("user")})
        cashier_names = []
        for u in unique_users:
            full_name = frappe.db.get_value("User", u, "full_name") or u
            cashier_names.append(full_name)
        self.cashiers = ", ".join(cashier_names)
        
        if self.include_stock_balances:
            self.aggregate_stock_balances(closing_entries)
        
        self.save()
        frappe.msgprint("Report Generated Successfully")

    def clear_existing_data(self):
        self.set("eod_item_sales", [])
        self.set("eod_item_group_sales", [])
        self.set("eod_payment_summary", [])
        self.set("eod_expense_breakdown", [])
        self.set("eod_discrepancies", [])
        self.set("eod_stock_balance", [])
        self.cashiers = ""
        self.total_expected_amount = 0.0
        self.total_actual_amount = 0.0
        self.total_difference = 0.0
        self.vat_amount = 0.0
        self.service_charge = 0.0
        self.consumption_tax = 0.0
        self.net_sales = 0.0
        self.total_taxes = 0.0
        self.total_transactions = 0
        
    def get_closing_entries(self):
        from frappe.utils import getdate, add_days

        # Shift dates by 1 day based on user request ("if I pick 11, it generates for 12")
        from_date = add_days(getdate(self.from_date_time), 1)
        to_date = add_days(getdate(self.to_date_time), 1)

        filters = {
            "company": self.company,
            "posting_date": ("between", [from_date, to_date]),
            "docstatus": 1
        }
        
        if self.pos_profiles:
            profiles = [row.pos_profile for row in self.pos_profiles]
            filters["pos_profile"] = ("in", profiles)
            
        return frappe.get_all("POS Closing Entry", filters=filters, fields=["name", "pos_profile", "grand_total", "net_total", "total_quantity", "user"])
        
    def aggregate_kpis(self, closing_entries):
        closing_entry_names = tuple([e.name for e in closing_entries])
        totals = frappe.db.sql("""
            SELECT SUM(expected_amount) as expected, SUM(closing_amount) as actual, SUM(difference) as diff
            FROM `tabPOS Closing Entry Detail`
            WHERE parent IN %s
        """, (closing_entry_names,), as_dict=True)[0]
        
        self.total_expected_amount = flt(totals.get("expected"))
        self.total_actual_amount = flt(totals.get("actual"))
        self.total_difference = flt(totals.get("diff"))
        
        self.vat_amount = self.total_expected_amount * 0.075
        self.service_charge = self.total_expected_amount * 0.10
        self.consumption_tax = self.total_expected_amount * 0.05
        
        self.net_sales = self.total_expected_amount - (self.vat_amount + self.service_charge + self.consumption_tax)

    def aggregate_invoices(self, closing_entry_names):
        # Get linked invoices from the child table of POS Closing Entry
        invoice_references = frappe.db.sql("""
            SELECT pos_invoice
            FROM `tabPOS Invoice Reference`
            WHERE parent IN %s
        """, (closing_entry_names,), as_dict=True)
        
        if not invoice_references:
            return
            
        invoice_names = tuple([r.pos_invoice for r in invoice_references])
        
        invoices = frappe.get_all(
            "POS Invoice", 
            filters={"name": ("in", invoice_names), "docstatus": 1},
            fields=["name", "net_total", "total_taxes_and_charges", "is_return"]
        )
        
        self.total_transactions = len(invoices)
        if not invoices:
            return
            
        submitted_invoice_names = tuple([i.name for i in invoices])
        
        for inv in invoices:
            multiplier = -1 if inv.is_return else 1
            self.total_taxes += flt(inv.total_taxes_and_charges) * multiplier

        item_sales = frappe.db.sql("""
            SELECT 
                i.item_code, 
                i.item_name, 
                i.item_group, 
                p.pos_profile, 
                SUM(CASE WHEN p.is_return = 1 THEN -i.qty ELSE i.qty END) as qty, 
                SUM(CASE WHEN p.is_return = 1 THEN -i.net_amount ELSE i.net_amount END) as amount
            FROM `tabPOS Invoice Item` i
            JOIN `tabPOS Invoice` p ON p.name = i.parent
            WHERE p.name IN %s
            GROUP BY i.item_code, p.pos_profile
        """, (submitted_invoice_names,), as_dict=True)
        
        for item in item_sales:
            self.append("eod_item_sales", {
                "pos_profile": item.pos_profile,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty_sold": item.qty,
                "amount": item.amount
            })
            
        group_sales = frappe.db.sql("""
            SELECT 
                i.item_group, 
                SUM(CASE WHEN p.is_return = 1 THEN -i.qty ELSE i.qty END) as qty, 
                SUM(CASE WHEN p.is_return = 1 THEN -i.net_amount ELSE i.net_amount END) as amount
            FROM `tabPOS Invoice Item` i
            JOIN `tabPOS Invoice` p ON p.name = i.parent
            WHERE p.name IN %s
            GROUP BY i.item_group
        """, (submitted_invoice_names,), as_dict=True)
        
        for group in group_sales:
            self.append("eod_item_group_sales", {
                "item_group": group.item_group,
                "qty_sold": group.qty,
                "amount": group.amount
            })

    def aggregate_payments(self, closing_entry_names):
        payments = frappe.db.sql("""
            SELECT mode_of_payment, SUM(expected_amount) as expected, SUM(closing_amount) as actual, SUM(difference) as diff
            FROM `tabPOS Closing Entry Detail`
            WHERE parent IN %s
            GROUP BY mode_of_payment
        """, (closing_entry_names,), as_dict=True)
        
        for p in payments:
            self.append("eod_payment_summary", {
                "payment_mode": p.mode_of_payment,
                "expected_amount": p.expected,
                "actual_amount": p.actual,
                "difference": p.diff
            })

    def flag_discrepancies(self, closing_entries):
        # We record every closing entry used in the report, including those with zero difference
        # This table serves as the "Associated Closing Entries" list
        
        closing_entry_names = tuple([e.name for e in closing_entries])
        differences = frappe.db.sql("""
            SELECT parent, SUM(difference) as diff
            FROM `tabPOS Closing Entry Detail`
            WHERE parent IN %s
            GROUP BY parent
        """, (closing_entry_names,), as_dict=True)
        
        diff_map = {d.parent: d.diff for d in differences}
        
        for entry in closing_entries:
            self.append("eod_discrepancies", {
                "pos_closing_entry": entry.name,
                "pos_profile": entry.pos_profile,
                "difference": diff_map.get(entry.name, 0.0)
            })

    def aggregate_stock_balances(self, closing_entries):
        # Collect unique POS profiles used in this report
        unique_profiles = list({e.pos_profile for e in closing_entries if e.pos_profile})
        if not unique_profiles:
            return

        for profile_name in unique_profiles:
            # Fetch the warehouse linked to this POS profile
            warehouse = frappe.db.get_value("POS Profile", profile_name, "warehouse")
            if not warehouse:
                continue

            # Get current stock balance (actual qty) per item from the Bin table
            stock_rows = frappe.db.sql("""
                SELECT
                    b.item_code,
                    i.item_name,
                    i.item_group,
                    i.stock_uom as uom,
                    b.actual_qty as balance_qty
                FROM `tabBin` b
                JOIN `tabItem` i ON i.name = b.item_code
                WHERE b.warehouse = %s
                  AND b.actual_qty != 0
                  AND i.disabled = 0
                ORDER BY i.item_group, i.item_name
            """, (warehouse,), as_dict=True)

            for row in stock_rows:
                self.append("eod_stock_balance", {
                    "pos_profile": profile_name,
                    "warehouse": warehouse,
                    "item_code": row.item_code,
                    "item_name": row.item_name,
                    "item_group": row.item_group,
                    "uom": row.uom,
                    "balance_qty": flt(row.balance_qty)
                })
