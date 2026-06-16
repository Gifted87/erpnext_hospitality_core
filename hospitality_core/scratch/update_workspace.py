import frappe

def update_workspace():
    try:
        frappe.init(site="185.170.58.232", sites_path="/home/erpnext/frappe-bench/sites")
        frappe.connect()
        
        updated = False
        # Update Hospitality Workspace
        if frappe.db.exists("Workspace", "Hospitality"):
            ws = frappe.get_doc("Workspace", "Hospitality")
            for link in ws.links:
                if link.label == "End of Day Report" or link.link_to == "End of Day Report":
                    link.label = "Frontdesk End of Day Report"
                    link.link_to = "Frontdesk End of Day Report"
                    updated = True
            
            if updated:
                ws.save(ignore_permissions=True)
                frappe.db.commit()
                print("Hospitality Workspace updated.")
            else:
                print("No links to 'End of Day Report' found in Hospitality Workspace.")
        else:
            print("Hospitality Workspace not found.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        frappe.destroy()

if __name__ == "__main__":
    update_workspace()
