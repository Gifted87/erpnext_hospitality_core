import frappe

def execute():
    # Rename doc
    doc_type = "DocType"
    old_name = "End of Day Sales Generator"
    new_name = "Sales Report"

    if frappe.db.exists(doc_type, old_name):
        frappe.rename_doc(doc_type, old_name, new_name, force=True)
        frappe.db.commit()
        print(f"Renamed {old_name} to {new_name}")
    else:
        print(f"{old_name} not found")
