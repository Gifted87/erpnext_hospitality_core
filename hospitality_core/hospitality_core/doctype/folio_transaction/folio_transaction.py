import frappe
from frappe import _
from frappe.model.document import Document

class FolioTransaction(Document):
    def before_insert(self):
        self.validate_parent_status()
        if not self.posting_time:
            self.posting_time = frappe.utils.nowtime()
        if not self.posted_by:
            self.posted_by = frappe.session.user
        self.compute_debit_credit()

    def compute_debit_credit(self):
        """Split the amount field into separate read-only debit and credit display columns."""
        amt = float(self.amount or 0)
        if self.is_void:
            self.debit = 0
            self.credit = 0
        elif amt >= 0:
            self.debit = amt
            self.credit = 0
        else:
            self.debit = 0
            self.credit = abs(amt)

    def after_insert(self):
        self.reorder_sibling_rows()

    def after_save(self):
        self.reorder_sibling_rows()

    def reorder_sibling_rows(self):
        """Re-assign idx on all sibling transactions so chronological order is reflected in the child table display."""
        if not self.parent:
            return
        rows = frappe.db.sql("""
            SELECT name
            FROM `tabFolio Transaction`
            WHERE parent = %s
            ORDER BY
                posting_date ASC,
                CASE WHEN posting_time IS NULL OR posting_time = '' THEN '00:00:00' ELSE posting_time END ASC,
                creation ASC
        """, self.parent, as_dict=False)

        for new_idx, (name,) in enumerate(rows, start=1):
            frappe.db.set_value("Folio Transaction", name, "idx", new_idx, update_modified=False)

    def validate(self):
        self.validate_void_status()
        self.fetch_price_if_missing()
        self.compute_debit_credit()


    def validate_parent_status(self):
        if self.parent:
            # Bypass validation for Payment Entries (Refunds/Payments can be applied to Closed folios)
            if self.reference_doctype == "Payment Entry":
                return
                
            # Check if parent exists before checking status (for testing isolation)
            if frappe.db.exists("Guest Folio", self.parent):
                parent_status = frappe.db.get_value("Guest Folio", self.parent, "status")
                if parent_status in ["Closed", "Cancelled"]:
                    frappe.throw(_("Cannot add transactions to a {0} Folio.").format(parent_status))

    def validate_void_status(self):
        # Prevent manual un-checking of 'Is Void' via list view or data import
        if self.is_new():
            return

        db_is_void = frappe.db.get_value("Folio Transaction", self.name, "is_void")
        if db_is_void and not self.is_void:
            frappe.throw(_("Cannot un-void a transaction. Create a new correction posting instead."))

    def fetch_price_if_missing(self):
        """
        Requirement: "price should be fetched automatically"
        If Item is selected but Amount is 0, fetch from Item Price (Standard Selling) or Item Standard Rate.
        """
        if self.item and not self.amount and not self.is_void:
            # 1. Try fetching from Item Price List (Standard Selling)
            price = frappe.db.get_value("Item Price", 
                {"item_code": self.item, "price_list": "Standard Selling"}, 
                "price_list_rate"
            )
            
            # 2. Fallback to Item Standard Rate
            if not price:
                price = frappe.db.get_value("Item", self.item, "standard_rate")
            
            if price:
                self.amount = float(price) * (self.qty or 1)
            
            # Auto-fetch description if missing
            if not self.description:
                self.description = frappe.db.get_value("Item", self.item, "item_name")