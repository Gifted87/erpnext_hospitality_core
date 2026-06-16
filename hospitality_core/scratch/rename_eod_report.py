import frappe

def rename_report():
    old_name = "End of Day Report"
    new_name = "Frontdesk End of Day Report"

    if frappe.db.exists("Report", old_name):
        frappe.rename_doc("Report", old_name, new_name, force=True)
        frappe.db.commit()
        print(f"Renamed Report {old_name} to {new_name}")
    else:
        print(f"Report {old_name} not found")

if __name__ == "__main__":
    rename_report()
