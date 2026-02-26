import frappe
import sys
import os

# Add apps directory to path 
sys.path.append('/home/erpnext/frappe-bench/apps/frappe')
sys.path.append('/home/erpnext/frappe-bench/apps/erpnext')
sys.path.append('/home/erpnext/frappe-bench/apps/hospitality_core')

def execute():
    frappe.init(site='185.170.58.232', sites_path='/home/erpnext/frappe-bench/sites')
    frappe.connect()

    try:
        print("Starting permission fix v2...")
        
        target_fields = ['reserved_by', 'hotel_reception', 'guest']
        
        for field in target_fields:
            # Update tabDocField
            frappe.db.sql(f"""
                UPDATE `tabDocField`
                SET ignore_user_permissions = 1
                WHERE parent = 'Hotel Reservation' AND fieldname = '{field}'
            """)
            print(f"Updated tabDocField for {field}: ignore_user_permissions = 1")

        # Also, check if there are Custom Fields?
        custom_fields = frappe.get_all("Custom Field", filters={"dt": "Hotel Reservation", "fieldname": ["in", target_fields]})
        for cf in custom_fields:
            frappe.db.set_value("Custom Field", cf.name, "ignore_user_permissions", 1)
            print(f"Updated Custom Field {cf.name}: ignore_user_permissions = 1")

        # Final commit
        frappe.db.commit()
        print("Database updates committed.")

        # Clear cache to ensure changes take effect immediately
        frappe.clear_cache(doctype="Hotel Reservation")
        print("Cache cleared for Hotel Reservation.")

    except Exception as e:
        print(f"Error: {e}")
        frappe.db.rollback()
    finally:
        frappe.destroy()

if __name__ == "__main__":
    execute()
