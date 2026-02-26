import frappe
import sys
import os

# Add apps directory to path 
sys.path.append('/home/erpnext/frappe-bench/apps/frappe')
sys.path.append('/home/erpnext/frappe-bench/apps/erpnext')
sys.path.append('/home/erpnext/frappe-bench/apps/hospitality_core')
# Add the apps root to allow hospitality_core.hospitality_core
sys.path.append('/home/erpnext/frappe-bench/apps')

from frappe.utils import nowdate

def execute():
    frappe.init(site="185.170.58.232", sites_path="../../sites")
    frappe.connect()

    try:
        # 1. Create Test Receptionist User
        user_email = "test_receptionist_v1@example.com"
        if not frappe.db.exists("User", user_email):
            user = frappe.new_doc("User")
            user.email = user_email
            user.first_name = "Test"
            user.last_name = "Receptionist"
            user.enabled = 1
            user.roles = []
            user.insert(ignore_permissions=True)
            
            # Add Hospitality User role
            user.add_roles("Hospitality User")
            frappe.db.commit()
            print(f"Created user: {user_email}")
        else:
            print(f"User {user_email} already exists.")

        # 2. Create a Reservation as Administrator
        # Need prerequisites: Hotel Reception, Guest, Room Type, Room
        if not frappe.db.exists("Hotel Reception", "Front Desk"):
             frappe.get_doc({"doctype":"Hotel Reception", "reception_name":"Front Desk"}).insert(ignore_permissions=True)
             
        if not frappe.db.exists("Hotel Room Type", "Standard"):
             frappe.get_doc({"doctype":"Hotel Room Type", "title":"Standard"}).insert(ignore_permissions=True)
             
        if not frappe.db.exists("Hotel Room", "101"):
             frappe.get_doc({"doctype":"Hotel Room", "room_number":"101", "room_type":"Standard", "status":"Available"}).insert(ignore_permissions=True)

        if not frappe.db.exists("Guest", {"full_name": "Admin Created Guest"}):
            g = frappe.new_doc("Guest")
            g.first_name = "Admin"
            g.last_name = "Created Guest"
            g.insert(ignore_permissions=True)
            guest_name = g.name
        else:
            guest_name = frappe.db.get_value("Guest", {"full_name": "Admin Created Guest"}, "name")

        res_name = "RES-ADMIN-TEST"
        if not frappe.db.exists("Hotel Reservation", {"guest": guest_name}):
            # Cleanup old test data
            frappe.db.sql("DELETE FROM `tabHotel Reservation` WHERE guest=%s", guest_name)
            
            res = frappe.new_doc("Hotel Reservation")
            res.hotel_reception = "Front Desk"
            res.guest = guest_name
            res.room_type = "Standard"
            res.room = "101"
            res.arrival_date = nowdate()
            res.departure_date = nowdate()
            res.status = "Reserved"
            res.insert(ignore_permissions=True)
            frappe.db.commit()
            res_name = res.name
            print(f"Created Reservation as Admin: {res_name}")
        else:
            res_name = frappe.db.get_value("Hotel Reservation", {"guest": guest_name}, "name")
            print(f"Using existing Reservation: {res_name}")

        # 3. Switch User and Try to Read
        frappe.set_user(user_email)
        print(f"Switched user to: {frappe.session.user}")
        
        # Try to get list
        reservations = frappe.get_list("Hotel Reservation", fields=["name", "guest", "reserved_by"])
        print(f"Visible Reservations for {user_email}: {len(reservations)}")
        
        found = False
        for r in reservations:
            if r.name == res_name:
                found = True
                print(f"SUCCESS: Can see admin reservation {r.name}")
        
        if not found:
            print(f"FAILURE: Cannot see admin reservation {res_name}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        frappe.destroy()

if __name__ == "__main__":
    execute()
