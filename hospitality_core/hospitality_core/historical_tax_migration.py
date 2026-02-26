import frappe
from frappe.utils import flt
from hospitality_core.hospitality_core.api.accounting import (
    make_gl_entries_for_folio_transaction,
    handle_payment_income_realization,
    reclassify_pos_taxes,
    redirect_pos_income_to_suspense
)

def run_migration():
    print("--- Starting Historical Tax Migration ---")
    
    # 1. Target Date Range
    start_date = "2026-01-01"
    end_date = "2026-01-17" # Migration ended on 15th, but let's be safe
    
    # 2. Identify Vouchers to cleanup
    # We target GL Entries in this range hitting Income, Suspense, or Receivable
    settings = frappe.get_single("Hospitality Accounting Settings")
    
    # a. Folio Transactions
    txns = frappe.get_all("Folio Transaction", filters={
        "posting_date": ["between", [start_date, end_date]],
        "item": ["!=", "PAYMENT"] # Payments handled separately
    }, fields=["name", "parent", "amount", "posting_date", "item", "description", "reference_doctype"])
    
    print(f"Found {len(txns)} Folio Transactions to re-process.")
    
    for txn in txns:
        # Delete existing GL entries for this transaction
        # Search by remarks containing Ref: txn.name
        frappe.db.sql("""
            DELETE FROM `tabGL Entry` 
            WHERE voucher_type = 'Guest Folio' 
            AND voucher_no = %s 
            AND remarks LIKE %s
        """, (txn.parent, f"%Ref: {txn.name}%"))
        
        # Re-run logic
        # Need to convert txn dict to doc-like object
        txn_doc = frappe.get_doc("Folio Transaction", txn.name)
        make_gl_entries_for_folio_transaction(txn_doc)
        
    print("✔ Folio Transactions re-processed.")

    # b. Payment Entries
    pes = frappe.get_all("Payment Entry", filters={
        "posting_date": ["between", [start_date, end_date]],
        "reference_no": ["like", "HIST-%"]
    }, fields=["name", "paid_amount", "posting_date", "reference_no"])
    
    print(f"Found {len(pes)} Payment Entries to re-process.")
    
    for pe in pes:
        # Delete realization GL entries
        frappe.db.sql("""
            DELETE FROM `tabGL Entry` 
            WHERE voucher_type = 'Payment Entry' 
            AND voucher_no = %s 
            AND (remarks LIKE 'Income Realization%%' OR remarks LIKE 'Income Realization (Net)%%')
        """, (pe.name,))
        
        # Re-run logic
        pe_doc = frappe.get_doc("Payment Entry", pe.name)
        handle_payment_income_realization(pe_doc, pe.reference_no, pe.paid_amount)
        
    print("✔ Payment Entries re-processed.")

    # c. POS Invoices (if any)
    # Even if not in script, user said "from everything sold"
    pos_invs = frappe.get_all("POS Invoice", filters={
        "posting_date": ["between", [start_date, end_date]],
        "docstatus": 1
    }, fields=["name", "grand_total", "posting_date"])
    
    print(f"Found {len(pos_invs)} POS Invoices to re-process.")
    
    for inv in pos_invs:
        # Delete tax reclassification and redirect entries
        frappe.db.sql("""
            DELETE FROM `tabGL Entry` 
            WHERE voucher_type = 'POS Invoice' 
            AND voucher_no = %s 
            AND (remarks LIKE 'Tax Reclassification%%' OR remarks LIKE 'Deferring Income%%')
        """, (inv.name,))
        
        # Re-run logic
        inv_doc = frappe.get_doc("POS Invoice", inv.name)
        reclassify_pos_taxes(inv_doc)
        redirect_pos_income_to_suspense(inv_doc)
        
    print("✔ POS Invoices re-processed.")

    frappe.db.commit()
    print("--- MIGRATION COMPLETE ---")

if __name__ == "__main__":
    run_migration()
