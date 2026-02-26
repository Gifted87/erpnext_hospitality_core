
import frappe

def run():
    ws = frappe.get_doc("Workspace", "Hospitality")
    
    report_names = [
        "House List", "Daily Arrivals", "Daily Departures", "Room Availability Report",
        "Maintenance Log Report", "Daily Sales Consumption", "Daily Payment Collection",
        "Gross Revenue Report", "Hospitality Expense Report", "Guest Ledger",
        "City Ledger", "Folio Balance Summary", "Void and Allowance Report",
        "Discount and Complimentary Report", "Hotel Performance Analytics", "End of Day Report"
    ]
    
    count = 0
    for link in ws.links:
        if link.link_type == "Report" and link.link_to in report_names:
            link.is_query_report = 1
            link.report_ref_doctype = ""
            count += 1
            print(f"Patched {link.label}")
            
    if count > 0:
        ws.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"Successfully patched {count} links in Workspace 'Hospitality'.")
    else:
        print("No matching report links found in Workspace.")

if __name__ == "__main__":
    run()
