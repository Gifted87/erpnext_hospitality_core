
import frappe
from frappe.utils import nowdate
from hospitality_core.hospitality_core.api.pos_bridge import process_room_charge

def test_pos_restriction():
    # 1. Setup: Create a Hotel Reservation & Folio
    print("Setting up test data...")
    if not frappe.db.exists("Hotel Room", "101"):
        frappe.get_doc({"doctype": "Hotel Room", "room_number": "101", "status": "Available", "is_group_room": 0}).insert()

    # Create distinct guests for each run to avoid linking issues
    import time
    ts = str(int(time.time()))
    guest_name = f"Test Guest {ts}"
    if not frappe.db.exists("Guest", guest_name):
        frappe.get_doc({"doctype": "Guest", "first_name": "Test", "last_name": f"Guest {ts}", "guest_type": "Private"}).insert()

    res = frappe.get_doc({
        "doctype": "Hotel Reservation",
        "hotel_reception": "Front Desk",
        "guest": frappe.db.get_value("Guest", {"last_name": f"Guest {ts}"}, "name"),
        "room_type": "Standard", # Ensure this exists or use a valid one
        "room": "101",
        "arrival_date": nowdate(),
        "departure_date": nowdate(),
        "status": "Reserved",
        "naming_series": "HR-.YYYY.-",
        "allow_pos_posting": 1 # Initially Allowed
    })
    res.insert()
    res.process_check_in()
    frappe.db.commit()
    
    print(f"Created Reservation {res.name} for Room 101. allow_pos_posting = {res.allow_pos_posting}")

    # 2. Test Success Case
    print("Testing Success Case (Allowed)...")
    pos_invoice = frappe.new_doc("POS Invoice")
    pos_invoice.customer = frappe.db.get_value("Guest", res.guest, "customer") # Assume Guest has customer created by system or manual
    # Mocking POS Invoice structure for process_room_charge
    pos_invoice.hotel_room = "101"
    pos_invoice.grand_total = 100
    pos_invoice.payments = [frappe._dict({"mode_of_payment": "Room Charge", "amount": 100})]
    pos_invoice.items = [frappe._dict({"item_code": "Test Item", "qty": 1, "amount": 100, "item_name": "Test Item"})]
    pos_invoice.name = f"POS-{ts}"
    pos_invoice.posting_date = nowdate()
    
    # Needs to be persisted for some checks
    # But process_room_charge takes a doc object.
    
    try:
        process_room_charge(pos_invoice)
        print("PASS: POS Posting allowed as expected.")
    except Exception as e:
        print(f"FAIL: POS Posting failed unexpectedly: {e}")

    # 3. Test Failure Case
    print("Testing Restricted Case (Not Allowed)...")
    res.allow_pos_posting = 0
    res.save()
    frappe.db.commit()
    print("Updated allow_pos_posting = 0")

    try:
        process_room_charge(pos_invoice)
        print("FAIL: POS Posting was allowed but should have been blocked.")
    except Exception as e:
        if "closed for POS Posting" in str(e):
            print("PASS: POS Posting blocked as expected.")
        else:
             print(f"FAIL: Unexpected error message: {e}")

    # Cleanup (Optional, but good for repeatability if using static room)
    # frappe.delete_doc("Hotel Reservation", res.name)

# test_pos_restriction()
