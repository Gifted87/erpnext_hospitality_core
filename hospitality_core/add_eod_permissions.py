import frappe

def execute():
    doc = frappe.get_doc("DocType", "End of Day Sales Generator")
    # Clear existing to be safe
    doc.permissions = []
    
    doc.append("permissions", {
        "role": "System Manager",
        "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 0, "cancel": 0, "amend": 0
    })
    doc.append("permissions", {
        "role": "Hospitality User",
        "read": 1, "write": 1, "create": 1, "delete": 0
    })
    doc.save()
    frappe.db.commit()
    print("Permissions added successfully.")
