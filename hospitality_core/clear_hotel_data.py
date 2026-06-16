import frappe

def execute():
    # 1. List of Doctypes to clear
    tables_to_clear = [
        "Hotel Reservation",
        "Hotel Group Booking",
        "Guest Folio",
        "Folio Transaction",
        "Folio Transaction Move Log",
        "Guest Balance Ledger",
        "Reservation Routing"
    ]
    
    print("Starting data wipe for hotel reservations, guest folios, and city ledger data (master folios)...")
    
    for doctype in tables_to_clear:
        try:
            table_name = f"tab{doctype}"
            
            # Count records for reporting
            count = frappe.db.sql(f"SELECT COUNT(*) FROM `{table_name}`")
            if count:
                 count = count[0][0]
            else:
                 count = 0
            
            # Clear the table
            frappe.db.sql(f"DELETE FROM `{table_name}`")
            
            # Some doctypes have child tables that also need clearing
            if doctype == "Hotel Reservation":
                frappe.db.sql("DELETE FROM `tabHotel Reservation Taxes and Charges`", ignore_ddl=True)
            if doctype == "Hotel Group Booking":
                frappe.db.sql("DELETE FROM `tabHotel Group Booking Room`", ignore_ddl=True)
                
            print(f"✔ Cleared {count} records from {doctype}")
            
        except frappe.db.ProgrammingError as pe:
            # Ignore if table doesn't exist just in case
            pass
        except Exception as e:
            print(f"✘ Could not clear {doctype}: {str(e)}")

    print("Resetting Room Statuses to Available...")
    try:
        frappe.db.sql("UPDATE `tabHotel Room` SET status = 'Available'")
        print("✔ Room statuses reset.")
    except Exception as e:
        print(f"✘ Could not reset rooms: {e}")

    frappe.db.commit()
    print("--- Wipe Complete ---")
