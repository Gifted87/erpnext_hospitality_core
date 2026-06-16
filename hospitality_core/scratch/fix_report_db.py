import frappe
from frappe.model.rename_doc import rename_doc

def fix_report():
    old = "End of Day Report"
    new = "Frontdesk End of Day Report"
    
    try:
        frappe.init(site="185.170.58.232", sites_path="/home/erpnext/frappe-bench/sites")
        frappe.connect()
        
        if frappe.db.exists("Report", old):
            print(f"Found {old}. Renaming to {new}...")
            if frappe.db.exists("Report", new):
                print(f"{new} already exists. Deleting {old}...")
                frappe.delete_doc("Report", old, ignore_permissions=True)
            else:
                rename_doc("Report", old, new, force=True)
            
            frappe.db.commit()
            print("Successfully updated database.")
        else:
            print(f"Report '{old}' not found in database.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        frappe.destroy()

if __name__ == "__main__":
    fix_report()
