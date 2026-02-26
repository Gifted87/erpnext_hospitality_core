import frappe
from frappe import _

def process_payment_entry(doc, method=None):
    """
    Hook: Payment Entry (on_submit, on_cancel)
    Logic: If Reference No matches a Guest Folio ID, post or void a credit transaction to that Folio.
    """
    # Check if linked to Folio via Reference No
    # We expect reference_no to hold the Folio ID (e.g., FOLIO-...)
    if not doc.reference_no or not frappe.db.exists("Guest Folio", doc.reference_no):
        return
        
    folio_name = doc.reference_no
    
    # Determine Amount (Paid Amount is usually positive in Payment Entry)
    amount = doc.paid_amount

    if doc.docstatus == 1: # On Submit
        # We need a negative amount to reduce the Folio Balance.
        credit_amount = -1 * abs(amount)
        
        # Ensure Payment Item Exists
        item_code = "PAYMENT"
        if not frappe.db.exists("Item", item_code):
            item = frappe.new_doc("Item")
            item.item_code = item_code
            item.item_name = "Payment Credit"
            item.item_group = "Services" if frappe.db.exists("Item Group", "Services") else "All Item Groups"
            item.is_stock_item = 0
            item.insert(ignore_permissions=True)
        
        # Insert Transaction
        frappe.get_doc({
            "doctype": "Folio Transaction",
            "parent": folio_name,
            "parenttype": "Guest Folio",
            "parentfield": "transactions",
            "posting_date": doc.posting_date,
            "item": item_code,
            "description": f"Payment Entry: {doc.name} ({doc.mode_of_payment})",
            "qty": 1,
            "amount": credit_amount,
            "bill_to": "Guest", 
            "reference_doctype": "Payment Entry",
            "reference_name": doc.name,
            "is_invoiced": 0  # Payments are not invoices
        }).insert(ignore_permissions=True)
        
        # Handle Accounting: Suspense -> Income transfer
        from hospitality_core.hospitality_core.api.accounting import handle_payment_income_realization
        handle_payment_income_realization(doc, folio_name, amount)
        
        frappe.msgprint(_("Payment of {0} successfully recorded on Folio {1}").format(amount, folio_name))

    elif doc.docstatus == 2: # On Cancel
        # 1. Find and Delete the Folio Transaction
        frappe.db.delete("Folio Transaction", {
            "reference_doctype": "Payment Entry",
            "reference_name": doc.name
        })
        
        # 2. Reverse Accounting Realization
        from hospitality_core.hospitality_core.api.accounting import handle_payment_income_realization
        handle_payment_income_realization(doc, folio_name, amount, cancel=1)
    
    # Sync Balance
    from hospitality_core.hospitality_core.api.folio import sync_folio_balance
    sync_folio_balance(frappe.get_doc("Guest Folio", folio_name))