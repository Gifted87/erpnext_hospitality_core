
import json
import frappe

def fix_and_sync():
    file_path = '/home/erpnext/frappe-bench/apps/hospitality_core/hospitality_core/hospitality_core/workspace/hospitality/hospitality.json'
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    report_links = [
        "House List", "Daily Arrivals", "Daily Departures", "Room Availability Report",
        "Maintenance Log Report", "Daily Sales Consumption", "Daily Payment Collection",
        "Gross Revenue Report", "Hospitality Expense Report", "Guest Ledger",
        "City Ledger", "Folio Balance Summary", "Void and Allowance Report",
        "Discount and Complimentary Report", "Hotel Performance Analytics", "End of Day Report"
    ]
    
    changed = False
    for link in data.get('links', []):
        if link.get('label') in report_links and link.get('link_type') == 'Report':
            link['link_type'] = 'URL'
            link['url'] = f"/app/query-report/{link['link_to']}"
            link['link_to'] = "" # Clear link_to for URL type
            changed = True

    if changed:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=1)
        print("Updated JSON with direct URLs.")
        
        # Now Sync to DB
        ws = frappe.get_doc("Workspace", "Hospitality")
        ws.links = []
        for l in data['links']:
            ws.append("links", l)
        ws.save()
        frappe.db.commit()
        print("Successfully synced Workspace 'Hospitality' to Database.")
    else:
        print("No changes needed in JSON.")

if __name__ == "__main__":
    fix_and_sync()
