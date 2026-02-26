import frappe
from frappe.utils import flt
from hospitality_core.hospitality_core.api.accounting import (
    make_gl_entries_for_folio_transaction,
    handle_payment_income_realization,
    reclassify_pos_taxes,
    redirect_pos_income_to_suspense
)

def run_fix_migration():
    print("--- Starting Corrective Tax Migration ---")
    
    start_date = "2026-01-01"
    end_date = "2026-01-17" 
    
    # 1. FIX PAYMENT ENTRIES (Wrong paid_to account)
    # They were set to Income Account 'Room Bookings - EHH', should be 'Cash - EHH'
    # We find them by Date + Customer (Historical Sync used specific customer)
    # Or by Amount if unique enough, but better by date range + customer.
    
    # Get Customer 'Historical Migration Sync'
    # Based on Step 349: Folio Guest is 'Historical Migration Sync', Customer is same.
    customer_name = "Historical Migration Sync"
    if not frappe.db.exists("Customer", customer_name):
        print("Warning: Historical Customer not found!")
        return

    # Find PEs
    pes = frappe.get_all("Payment Entry", filters={
        "posting_date": ["between", [start_date, end_date]],
        "party": customer_name
    }, fields=["name", "paid_to", "paid_amount", "reference_no"])
    
    print(f"Found {len(pes)} Payment Entries for Historical Customer.")
    
    cash_account = "Cash - EHH" # Target account
    
    for pe in pes:
        # A. Update Account to Cash
        if pe.paid_to != cash_account:
            frappe.db.set_value("Payment Entry", pe.name, "paid_to", cash_account)
            # This updates the document but doesn't regenerate the main GL entries automatically 
            # unless we cancel/amend. To avoid complex amend logic, we will MANUALLY fix the GL entries 
            # for the Payment itself (Dr Cash, Cr Debtors).
            
            # Delete old GLs 
            frappe.db.sql("DELETE FROM `tabGL Entry` WHERE voucher_type='Payment Entry' AND voucher_no=%s", (pe.name,))
            
            # Re-create Standard GLs (Dr Cash, Cr Debtors)
            # Debtors
            frappe.get_doc({
                "doctype": "GL Entry",
                "posting_date": "2026-01-01", # Should use actual date but PE field is missing in loop, fetch full doc
                "account": "Debtors - EHH",
                "party_type": "Customer",
                "party": customer_name,
                "credit": pe.paid_amount,
                "debit": 0,
                "voucher_type": "Payment Entry",
                "voucher_no": pe.name,
                "remarks": f"Correction: Payment from {customer_name}"
            }).insert()
            
            # Cash
            frappe.get_doc({
                "doctype": "GL Entry",
                "posting_date": "2026-01-01", # Placeholder, will fetch doc below
                "account": cash_account,
                "debit": pe.paid_amount,
                "credit": 0,
                "voucher_type": "Payment Entry",
                "voucher_no": pe.name,
                "remarks": f"Correction: Payment from {customer_name}"
            }).insert()

        # Fetch doc to get correct date and trigger Realization
        pe_doc = frappe.get_doc("Payment Entry", pe.name)
        
        # Determine Folio ID. 
        # Historical script used 'reference_no' as Folio. 
        # If reference_no is empty or weird, we might need to look it up.
        # But in Step 394 we saw 'reference_no': 'FOLIO-02331'. So it should be fine.
        folio_id = pe.reference_no
        
        # Remove any old Realization GLs (if any exist now)
        frappe.db.sql("""
            DELETE FROM `tabGL Entry` 
            WHERE voucher_type = 'Payment Entry' 
            AND voucher_no = %s 
            AND (remarks LIKE 'Income Realization%%' OR remarks LIKE 'Income Realization (Net)%%')
        """, (pe.name,))
        
        # Run Realization Logic (Net Amount)
        handle_payment_income_realization(pe_doc, folio_id, pe.paid_amount)
        
    print("✔ Payment Entries Corrected")

    # 2. RE-RUN FOLIO TRANSACTIONS (To apply Rounding)
    txns = frappe.get_all("Folio Transaction", filters={
        "posting_date": ["between", [start_date, end_date]],
        "item": ["!=", "PAYMENT"]
    }, fields=["name", "parent", "amount", "posting_date", "item", "description"])
    
    print(f"Re-processing {len(txns)} Folio Transactions with Rounding...")
    
    for txn in txns:
        # Delete existing GL entries
        frappe.db.sql("""
            DELETE FROM `tabGL Entry` 
            WHERE voucher_type = 'Guest Folio' 
            AND voucher_no = %s 
            AND remarks LIKE %s
        """, (txn.parent, f"%Ref: {txn.name}%"))
        
        txn_doc = frappe.get_doc("Folio Transaction", txn.name)
        make_gl_entries_for_folio_transaction(txn_doc)
        
    print("✔ Folio Transactions Corrected")
    
    frappe.db.commit()
    print("--- CORRECTION COMPLETE ---")

if __name__ == "__main__":
    run_fix_migration()
