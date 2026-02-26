
import frappe
from frappe.utils import nowdate, flt
import time

def run_test():
    print("Starting POS Cancellation Fix Verification Test...")
    
    # 1. Setup Data
    company = "Edo Heritage Hotel"
    ts = str(int(time.time()))
    room_number = "101TEST"
    item_code = "TEST_BEER"
    guest_name = f"Test Guest {ts}"
    
    if not frappe.db.exists("Hotel Room", room_number):
        frappe.get_doc({"doctype": "Hotel Room", "room_number": room_number, "status": "Available", "is_group_room": 0}).insert()

    if not frappe.db.exists("Guest", guest_name):
        guest = frappe.get_doc({
            "doctype": "Guest", 
            "first_name": "Test", 
            "last_name": f"Guest {ts}", 
            "guest_type": "Private"
        }).insert(ignore_permissions=True)
        customer = guest.customer
    else:
        customer = frappe.db.get_value("Guest", guest_name, "customer")

    if not frappe.db.exists("Item", item_code):
        frappe.get_doc({
            "doctype": "Item",
            "item_code": item_code,
            "item_name": "Test Beer",
            "item_group": "Products",
            "is_stock_item": 0,
            "opening_stock": 0,
            "valuation_rate": 0,
            "standard_rate": 2000
        }).insert()

    # Create Reservation & Check-in
    res = frappe.get_doc({
        "doctype": "Hotel Reservation",
        "company": company,
        "hotel_reception": "Front Desk",
        "guest": frappe.db.get_value("Guest", {"last_name": f"Guest {ts}"}, "name"),
        "room_type": "Standard",
        "room": room_number,
        "arrival_date": nowdate(),
        "departure_date": nowdate(),
        "status": "Reserved",
        "allow_pos_posting": 1
    }).insert(ignore_permissions=True)
    res.process_check_in()
    
    folio_name = frappe.db.get_value("Guest Folio", {"reservation": res.name}, "name")
    print(f"Checkout Reservation: {res.name}, Folio: {folio_name}")

    # 2. Create POS Invoice
    pos_profile = frappe.db.get_value("POS Profile", {"company": company}, "name")
    if not pos_profile:
        print("FAIL: No POS Profile found for company")
        return

    pos_inv = frappe.get_doc({
        "doctype": "POS Invoice",
        "company": company,
        "customer": customer,
        "pos_profile": pos_profile,
        "posting_date": nowdate(),
        "hotel_room": room_number,
        "update_stock": 0,
        "items": [
            {
                "item_code": item_code,
                "qty": 1,
                "rate": 2450, # 2450 / 1.225 = 2000 Net
                "amount": 2450
            }
        ],
        "payments": [
            {
                "mode_of_payment": "Room Charge",
                "amount": 2450,
                "account": frappe.db.get_value("Mode of Payment Account", {"parent": "Room Charge", "company": company}, "default_account")
            }
        ]
    })
    
    pos_inv.insert(ignore_permissions=True)
    pos_inv.submit()
    print(f"Submitted POS Invoice: {pos_inv.name}")

    # 3. Verify GL Entries
    gl_entries = frappe.get_all("GL Entry", filters={"voucher_no": pos_inv.name, "is_cancelled": 0})
    print(f"Found {len(gl_entries)} GL entries for {pos_inv.name}")
    
    # We expect custom GL entries from our hooks:
    # 1. Reclassify POS Taxes
    # 2. Redirect POS Income to Suspense
    
    for gle in gl_entries:
        print(f"  GLE: Account: {gle.account}, Debit: {gle.debit}, Credit: {gle.credit}")

    # 4. Cancel POS Invoice
    try:
        pos_inv.cancel()
        print(f"Successfully cancelled POS Invoice: {pos_inv.name}")
    except Exception as e:
        print(f"FAIL: Cancellation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. Verify Reversal
    gl_entries_cancelled = frappe.get_all("GL Entry", filters={"voucher_no": pos_inv.name, "is_cancelled": 1})
    print(f"Found {len(gl_entries_cancelled)} reversal GL entries for {pos_inv.name}")
    
    for gle in gl_entries_cancelled:
         print(f"  REVERSAL GLE: Account: {gle.account}, Debit: {gle.debit}, Credit: {gle.credit}")

    if len(gl_entries_cancelled) > 0:
        print("PASS: Reversal GL entries created.")
    else:
        print("FAIL: No reversal GL entries found.")

    # 6. Check Folio Transactions
    txn_count = frappe.db.count("Folio Transaction", {"reference_name": pos_inv.name})
    if txn_count == 0:
        print("PASS: Folio Transactions deleted upon cancellation.")
    else:
        print(f"FAIL: {txn_count} Folio Transactions still exist.")

if __name__ == "__main__":
    run_test()
