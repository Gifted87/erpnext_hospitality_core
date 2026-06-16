import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def add_custom_fields():
    create_custom_field('Payment Entry', {
        'fieldname': 'room_number',
        'label': 'Room Number',
        'fieldtype': 'Data',
        'insert_after': 'party_name',
        'print_hide': 0
    })
    frappe.db.commit()
    print("Custom field added successfully.")
