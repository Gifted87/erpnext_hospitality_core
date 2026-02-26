import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "label": _("Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Voucher Type"),
            "fieldname": "voucher_type",
            "fieldtype": "Link",
            "options": "DocType",
            "width": 120
        },
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 150
        },
        {
            "label": _("Description"),
            "fieldname": "remarks",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": _("Account"),
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 150
        },
        {
            "label": _("Consumption Tax (5%)"),
            "fieldname": "ct_amount",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("VAT (7.5%)"),
            "fieldname": "vat_amount",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Service Charge (10%)"),
            "fieldname": "sc_amount",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Total Deductions"),
            "fieldname": "total_deductions",
            "fieldtype": "Currency",
            "width": 120
        }
    ]

def get_data(filters):
    settings = frappe.get_single("Hospitality Accounting Settings")
    tax_accounts = [
        settings.consumption_tax_account,
        settings.vat_account,
        settings.service_charge_account
    ]
    
    # Remove None values
    tax_accounts = [acc for acc in tax_accounts if acc]
    
    if not tax_accounts:
        return []

    conditions = []
    if filters.get("from_date"):
        conditions.append(f"posting_date >= '{filters.get('from_date')}'")
    if filters.get("to_date"):
        conditions.append(f"posting_date <= '{filters.get('to_date')}'")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    gl_entries = frappe.db.sql(f"""
        SELECT 
            posting_date, voucher_type, voucher_no, remarks, account, credit, debit
        FROM 
            `tabGL Entry`
        WHERE 
            account IN ({', '.join(['%s']*len(tax_accounts))})
            AND {where_clause}
            AND is_cancelled = 0
        ORDER BY 
            posting_date DESC, voucher_no DESC
    """, tuple(tax_accounts), as_dict=1)

    data = []
    
    # Group by voucher to show a single row per transaction with splits
    # or just show row by row. Usually, users want to see the total per invoice.
    # However, since they hit different accounts, they are separate GL entries.
    
    for entry in gl_entries:
        row = {
            "posting_date": entry.posting_date,
            "voucher_type": entry.voucher_type,
            "voucher_no": entry.voucher_no,
            "remarks": entry.remarks,
            "account": entry.account,
            "ct_amount": 0,
            "vat_amount": 0,
            "sc_amount": 0,
            "total_deductions": 0
        }
        
        # In tax accounts, Credit is a positive tax liability
        amount = flt(entry.credit) - flt(entry.debit)
        
        if entry.account == settings.consumption_tax_account:
            row["ct_amount"] = amount
        elif entry.account == settings.vat_account:
            row["vat_amount"] = amount
        elif entry.account == settings.service_charge_account:
            row["sc_amount"] = amount
            
        row["total_deductions"] = amount
        data.append(row)

    return data
