import frappe
from frappe import _

@frappe.whitelist()
def void_transaction(folio_transaction_name, reason_code):
    """
    Marks a transaction as Void.
    """
    if not ("Frontdesk Supervisor" in frappe.get_roles() or frappe.session.user == "Administrator"):
        frappe.throw(_("Access Denied. Only Frontdesk Supervisors can void transactions."))

    # 1. Fetch Transaction
    trans = frappe.get_doc("Folio Transaction", folio_transaction_name)
    
    if trans.is_invoiced:
        frappe.throw(_("Cannot void this transaction because it has already been invoiced (Sales Invoice generated). Create a Credit Note instead."))

    if trans.is_void:
        frappe.throw(_("Transaction is already void."))

    # 2. Check Permissions / Approval
    reason_doc = frappe.get_doc("Allowance Reason Code", reason_code)
    if reason_doc.requires_manager_approval:
        if not ("Frontdesk Supervisor" in frappe.get_roles() or frappe.session.user == "Administrator"):
            frappe.throw(_("This Reason Code requires Supervisor Approval."))

    # 3. Update Transaction
    frappe.db.set_value("Folio Transaction", trans.name, {
        "is_void": 1,
        "void_reason": reason_code,
        "amount": 0 # Zero out amount so it doesn't affect balance, OR keep amount but exclude in SQL. 
                    # Logic in 'sync_folio_balance' handles 'is_void=1' by ignoring it.
                    # Best practice: Keep the amount for audit, ignore in sum.
    })

    # 4. Trigger Recalculation
    from hospitality_core.hospitality_core.api.folio import sync_folio_balance
    sync_folio_balance(frappe.get_doc("Guest Folio", trans.parent))

    frappe.msgprint(_("Transaction Voided Successfully."))