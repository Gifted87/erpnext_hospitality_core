import frappe

def execute():
    # Fetch all Paid POS Invoices for the "Bush Bar" profile
    # Using case-insensitive search just in case
    invoices = frappe.get_all(
        "POS Invoice",
        filters={
            "docstatus": 1,
            "status": "Paid",
            "pos_profile": ["like", "%bush bar%"]
        },
        pluck="name"
    )
    
    if not invoices:
        print("No Paid POS Invoices found for 'Bush Bar'.")
        return

    print(f"Forcing cancellation of {len(invoices)} invoices...")
    
    for inv_name in invoices:
        try:
            # 1. Update POS Invoice docstatus
            frappe.db.sql("UPDATE `tabPOS Invoice` SET docstatus=2 WHERE name=%s", (inv_name,))
            
            # 2. Update linked GL Entries
            frappe.db.sql("UPDATE `tabGL Entry` SET docstatus=2, is_cancelled=1 WHERE voucher_no=%s", (inv_name,))
            
            # 3. Update Stock Ledger Entries if any
            frappe.db.sql("UPDATE `tabStock Ledger Entry` SET docstatus=2 WHERE voucher_no=%s", (inv_name,))
            
            # 4. Update Payment Ledger Entries if any (v14+)
            try:
                frappe.db.sql("UPDATE `tabPayment Ledger Entry` SET docstatus=2 WHERE voucher_no=%s", (inv_name,))
            except Exception:
                pass # Table might not exist in older versions

            print(f"Force Cancelled: {inv_name}")
        except Exception as e:
            print(f"Failed to force cancel {inv_name}: {str(e)}")
            
    frappe.db.commit()
    print("Forced cancellation complete.")
