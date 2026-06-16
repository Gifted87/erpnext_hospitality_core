import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def setup():
    # 1. Create Point of Sale Report if not exists
    if not frappe.db.exists("Report", "Point of Sale Report"):
        frappe.get_doc({
            "doctype": "Report",
            "report_name": "Point of Sale Report",
            "ref_doctype": "POS Invoice",
            "report_type": "Script Report",
            "is_standard": "Yes",
            "module": "Hospitality Core"
        }).insert(ignore_permissions=True)
        print("Created Point of Sale Report")
    else:
        print("Point of Sale Report already exists")

    # 2. Add custom field Hotel Reception to Mode of Payment
    create_custom_field('Mode of Payment', {
        'fieldname': 'hotel_reception',
        'label': 'Hotel Reception',
        'fieldtype': 'Link',
        'options': 'Hotel Reception',
        'insert_after': 'type'
    })
    print("Added/Updated custom field hotel_reception to Mode of Payment")
    
if __name__ == "__main__":
    frappe.init(site="185.170.58.232")
    frappe.connect()
    try:
        setup()
        frappe.db.commit()
    finally:
        frappe.destroy()
