import frappe
import sys
import os
import json

# Add apps directory to path 
sys.path.append('/home/erpnext/frappe-bench/apps/frappe')
sys.path.append('/home/erpnext/frappe-bench/apps/erpnext')
sys.path.append('/home/erpnext/frappe-bench/apps/hospitality_core')

def execute():
    frappe.init(site='185.170.58.232', sites_path='/home/erpnext/frappe-bench/sites')
    frappe.connect()

    try:
        # 1. Inspect Meta
        meta = frappe.get_meta('Hotel Reservation')
        print(f"DocType: {meta.name}")
        
        for p in meta.permissions:
            if p.role in ['Hospitality User', 'System Manager', 'Front-Desk']:
                print(f"\n--- Role: {p.role} ---")
                p_dict = p.as_dict()
                for key in sorted(p_dict.keys()):
                    print(f"  {key}: {p_dict[key]}")

        # 2. Inspect Users
        print("\n--- User Role & Permission Check ---")
        users = ['neky4love2000@gmail.com', 'pezeanyika@gmail.com', 'ogunnubikemi@gmail.com', 'kalujessica62@gmail.com', 'adaezeokoli@gmail.com']
        for u in users:
            if frappe.db.exists("User", u):
                roles = frappe.get_roles(u)
                print(f"\nUser: {u}")
                print(f"  Roles: {roles}")
                
                # Check for User Permissions explicitly
                ups = frappe.get_all("User Permission", filters={"user": u}, fields=["allow", "for_value", "apply_to_all_doctypes"])
                print(f"  User Permissions: {ups}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        frappe.destroy()

if __name__ == "__main__":
    execute()
