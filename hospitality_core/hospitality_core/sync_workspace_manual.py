
import frappe
import json

def sync_workspace():
    # Load the JSON content
    with open('/home/erpnext/frappe-bench/apps/hospitality_core/hospitality_core/hospitality_core/workspace/hospitality/hospitality.json', 'r') as f:
        data = json.load(f)
    
    # Get the workspace document
    ws = frappe.get_doc("Workspace", "Hospitality")
    
    # Update links
    # We need to construct the links list from the JSON data
    new_links = []
    for link_data in data.get('links', []):
        new_links.append(link_data)
        
    # Replace existing links
    ws.links = []
    for l in new_links:
        ws.append("links", l)
        
    ws.save()
    frappe.db.commit()
    print("Workspace 'Hospitality' synced successfully from JSON.")

if __name__ == "__main__":
    sync_workspace()
