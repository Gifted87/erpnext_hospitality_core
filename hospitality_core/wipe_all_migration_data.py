import frappe

def wipe_financial_data():
    # 1. List of Doctypes to clear
    # Note: We use SQL because many of these are 'Immutable' or 'Submittable'
    # and standard delete_doc will throw errors.
    
    tables_to_clear = [
        "GL Entry",
        "Payment Entry",
        "Payment Ledger Entry",
        "Journal Entry",
        "Bank Transaction",
        "Hotel Reservation",
        "Guest Folio",
        "Folio Transaction"
    ]
    
    print("Starting data wipe...")
    
    for doctype in tables_to_clear:
        try:
            # Get the table name (e.g., tabGL Entry)
            table_name = f"tab{doctype}"
            
            # Count records for reporting
            count = frappe.db.sql(f"SELECT COUNT(*) FROM `{table_name}`")
            if count:
                 count = count[0][0]
            else:
                 count = 0
            
            # Clear the table
            frappe.db.sql(f"DELETE FROM `{table_name}`")
            
            # Clear associated 'Child Tables' for Payment/Journal Entries if they exist
            if doctype == "Payment Entry":
                frappe.db.sql("DELETE FROM `tabPayment Entry Reference`")
            if doctype == "Journal Entry":
                frappe.db.sql("DELETE FROM `tabJournal Entry Account`")
                
            print(f"✔ Cleared {count} records from {doctype}")
            
        except Exception as e:
            print(f"✘ Could not clear {doctype}: {str(e)}")

    frappe.db.commit()
    print("--- Wipe Complete ---")
