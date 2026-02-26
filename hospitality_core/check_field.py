
import frappe

def check_custom_field():
    exists = frappe.db.exists("Custom Field", {"dt": "POS Invoice", "fieldname": "hotel_room"})
    if exists:
        print("Custom Field 'hotel_room' exists.")
        doc = frappe.get_doc("Custom Field", {"dt": "POS Invoice", "fieldname": "hotel_room"})
        print(f"Details: {doc.as_dict()}")
    else:
        print("Custom Field 'hotel_room' DOES NOT EXIST.")

check_custom_field()
