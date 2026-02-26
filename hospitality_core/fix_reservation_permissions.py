import frappe

def execute():
    frappe.init(site="185.170.58.232", sites_path="../../sites")
    frappe.connect()

    try:
        print("Checking permissions for Hotel Reservation...")
        
        # 1. Update DocPerm
        # We want to ensure 'Hospitality User' can see ALL reservations, not just their own.
        # So if_owner needs to be 0.
        
        # Check current state
        perms = frappe.db.sql("""
            SELECT name, role, if_owner, `read`, `write`, `create` 
            FROM `tabDocPerm` 
            WHERE parent='Hotel Reservation' AND role='Hospitality User'
        """, as_dict=True)
        
        print(f"Current Permissions for Hospitality User: {perms}")
        
        # Update if_owner to 0
        frappe.db.sql("""
            UPDATE `tabDocPerm`
            SET if_owner = 0
            WHERE parent = 'Hotel Reservation' AND role = 'Hospitality User'
        """)
        
        frappe.db.commit()
        print("Updated DocPerm: Set if_owner = 0 for Hospitality User.")
        
        # 2. Check for User Permissions
        # Sometimes User Permissions (formerly Match Rules) can restrict visibility based on linked fields (e.g. User link)
        
        # See if there are any User Permissions for this user that might inadvertently filter Hotel Reservation
        # We can't know the specific reception user, but we can check if there are restriction on 'Hotel Reservation' doctype generally
        
        user_perms = frappe.db.sql("""
            SELECT * FROM `tabUser Permission` 
            WHERE allow = 'Hotel Reservation'
        """, as_dict=True)
        
        if user_perms:
            print(f"WARNING: Found {len(user_perms)} User Permission records for Hotel Reservation. These might restrict access.")
            for up in user_perms:
                print(f" - User: {up.user}, Allow: {up.allow}, For Value: {up.for_value}")
        else:
            print("No User Permission explicitly set on 'Hotel Reservation' Doctype.")

        # Also check if there are Global Defaults that might affect this? Unlikely for this specific issue.
        
        print("Done.")
        
    except Exception as e:
        print(f"Error: {e}")
        frappe.db.rollback()
    finally:
        frappe.destroy()

if __name__ == "__main__":
    execute()
