import frappe

def execute():
    doctypes_to_update = [
        "EOD POS Profile",
        "EOD Item Sales",
        "EOD Item Group Sales",
        "EOD Payment Summary",
        "EOD Expense Breakdown",
        "EOD Discrepancies",
        "End of Day Sales Generator"
    ]
    
    for dt in doctypes_to_update:
        if frappe.db.exists("DocType", dt):
            doc = frappe.get_doc("DocType", dt)
            doc.custom = 0
            doc.save()
            print(f"Made {dt} standard")
    frappe.db.commit()
