import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    doctype_name = "Folio Ledger Adjustment"
    
    if frappe.db.exists("DocType", doctype_name):
        print(f"DocType {doctype_name} already exists.")
        return

    doc = frappe.get_doc({
        "doctype": "DocType",
        "name": doctype_name,
        "module": "Hospitality Core",
        "custom": 1,
        "is_submittable": 1,
        "autoname": "naming_series:",
        "naming_rule": "By \"Naming Series\" field",
        "fields": [
            {
                "fieldname": "naming_series",
                "fieldtype": "Select",
                "label": "Series",
                "options": "ADJ-.YYYY.-",
                "reqd": 1,
                "set_only_once": 1
            },
            {
                "fieldname": "folio",
                "fieldtype": "Link",
                "label": "Folio",
                "options": "Guest Folio",
                "reqd": 1,
                "in_list_view": 1,
                "in_standard_filter": 1
            },
            {
                "fieldname": "adjustment_type",
                "fieldtype": "Select",
                "label": "Adjustment Type",
                "options": "Add Debt\nClear Debt",
                "reqd": 1,
                "in_list_view": 1,
                "in_standard_filter": 1
            },
            {
                "fieldname": "amount",
                "fieldtype": "Currency",
                "label": "Amount",
                "reqd": 1,
                "in_list_view": 1,
                "non_negative": 1,
                "description": "Enter the positive amount to adjust."
            },
            {
                "fieldname": "description",
                "fieldtype": "Data",
                "label": "Reason / Description",
                "reqd": 1
            },
            {
                "fieldname": "amended_from",
                "fieldtype": "Link",
                "label": "Amended From",
                "options": doctype_name,
                "read_only": 1,
                "print_hide": 1,
                "no_copy": 1
            }
        ],
        "permissions": [
            {
                "role": "System Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "submit": 1,
                "cancel": 1,
                "amend": 1
            },
            {
                "role": "Frontdesk Supervisor",
                "read": 1,
                "write": 1,
                "create": 1,
                "submit": 1,
                "cancel": 1,
                "amend": 1
            }
        ],
        "track_changes": 1,
        "track_views": 1,
        "document_type": "Document"
    })
    
    doc.insert(ignore_permissions=True)
    print(f"Created DocType {doctype_name}")
    
    # Ensure MANUAL_DEBT item exists
    item_code = "MANUAL_ADJUSTMENT"
    if not frappe.db.exists("Item", item_code):
        item = frappe.new_doc("Item")
        item.item_code = item_code
        item.item_name = "Manual Ledger Adjustment"
        item.item_group = "Services" if frappe.db.exists("Item Group", "Services") else "All Item Groups"
        item.is_stock_item = 0
        item.insert(ignore_permissions=True)
        print(f"Created Item {item_code}")

