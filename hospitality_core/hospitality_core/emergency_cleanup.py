import frappe
from hospitality_core.hospitality_core.api.accounting import make_gl_entries_for_folio_transaction

def run_cleanup():
    print("--- EMERGENCY CLEANUP OF DUPLICATES ---")
    
    start_date = "2026-01-01"
    end_date = "2026-01-17" 
    
    # 1. Get all Folios active in this period (approx) 
    # Actually, better to get Folio Transactions and group by Folio ID
    txns = frappe.get_all("Folio Transaction", filters={
        "posting_date": ["between", [start_date, end_date]],
        "item": ["!=", "PAYMENT"]
    }, fields=["name", "parent", "amount", "posting_date", "item", "description", "reference_doctype", "reference_name"])
    
    print(f"Found {len(txns)} transactions to clean up.")
    
    processed_folios = set()
    
    for txn in txns:
        if txn.parent in processed_folios:
            continue
            
        print(f"Cleaning Folio {txn.parent}...")
        
        # DELETE ALL GL Entries for this Folio
        # This wipes the slate clean for revenue/tax posting
        frappe.db.sql("DELETE FROM `tabGL Entry` WHERE voucher_type='Guest Folio' AND voucher_no=%s", (txn.parent,))
        
        # Now find ALL non-payment transactions for this folio and re-post
        folio_txns = frappe.get_all("Folio Transaction", filters={
            "parent": txn.parent,
            "item": ["!=", "PAYMENT"]
        }, fields=["name", "parent", "amount", "posting_date", "item", "description", "reference_doctype", "reference_name"])
        
        for f_txn in folio_txns:
            doc = frappe.get_doc("Folio Transaction", f_txn.name)
            # Ensure no double posting if multiple transactions per folio
            make_gl_entries_for_folio_transaction(doc)
            
        processed_folios.add(txn.parent)
        
    frappe.db.commit()
    print("--- CLEANUP COMPLETE ---")

if __name__ == "__main__":
    run_cleanup()
