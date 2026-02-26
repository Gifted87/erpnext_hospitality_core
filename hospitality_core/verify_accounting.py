import frappe
from frappe.utils import nowdate

def verify_accounting():
    print("--- Starting Accounting Verification ---")
    
    # 0. Check Settings
    settings = frappe.get_single("Hospitality Accounting Settings")
    print(f"Settings: Receivable={settings.receivable_account}, Suspense={settings.income_suspense_account}, Income={settings.income_account}")

    # 1. Setup Test Guest & Folio
    guest_name = "Accounting Test Guest"
    if not frappe.db.exists("Guest", guest_name):
        guest = frappe.new_doc("Guest")
        guest.full_name = guest_name
        guest.customer = "Walk in Customer" # Valid customer
        guest.insert()
    else:
        guest = frappe.get_doc("Guest", guest_name)

    folio = frappe.new_doc("Guest Folio")
    folio.guest = guest.name
    folio.room = "1001" # Valid room
    folio.status = "Open"
    folio.insert()
    print(f"Created Folio: {folio.name}")

    # 2. Add a Charge
    txn = frappe.get_doc({
        "doctype": "Folio Transaction",
        "parent": folio.name,
        "parenttype": "Guest Folio",
        "parentfield": "transactions",
        "posting_date": frappe.utils.nowdate(),
        "item": "ROOM-RENT",
        "description": "Verification Charge",
        "qty": 1,
        "amount": 50000,
        "bill_to": "Guest"
    })
    txn.insert(ignore_permissions=True)
    print(f"Created Transaction: {txn.name}")

    # 3. Check GL Entries for Charge
    gles = frappe.db.get_all("GL Entry", 
        filters={"remarks": ["like", f"%Ref: {txn.name}%"]},
        fields=["account", "debit", "credit"]
    )
    print(f"GL Entries for Charge: {gles}")
    
    # 4. Add a Payment via Payment Entry
    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Receive"
    pe.party_type = "Customer"
    pe.party = guest.customer
    pe.paid_amount = 50000
    pe.received_amount = 50000
    pe.target_exchange_rate = 1
    pe.posting_date = frappe.utils.nowdate()
    pe.company = "Edo Heritage Hotel"
    pe.paid_to = "Cash - EHH" # Or some bank
    pe.paid_from = "Debtors - EHH"
    pe.reference_no = folio.name
    pe.reference_date = frappe.utils.nowdate()
    # Mocking cashier and reception if needed
    pe.insert(ignore_permissions=True, ignore_mandatory=True)
    pe.submit()
    print(f"Created Payment Entry: {pe.name}")

    # 5. Check GL Entries for Realization
    real_gles = frappe.db.get_all("GL Entry",
        filters={"voucher_no": pe.name, "remarks": ["like", f"%Income Realization%"]},
        fields=["account", "debit", "credit"]
    )
    print(f"GL Entries for Realization: {real_gles}")

    # 6. Test POS Integration
    print("--- Testing POS Integration ---")
    pos = frappe.new_doc("POS Invoice")
    pos.company = "Edo Heritage Hotel"
    pos.customer = "Walk in Customer"
    pos.posting_date = frappe.utils.nowdate()
    # Add an item
    pos.append("items", {
        "item_code": "ROOM-RENT", # Just for testing
        "qty": 1,
        "rate": 10000,
        "amount": 10000,
        "income_account": settings.income_account,
        "cost_center": settings.cost_center,
        "warehouse": "Kitchen - EHH" # Valid warehouse
    })
    # Add payment
    pos.append("payments", {
        "mode_of_payment": "Room Charge",
        "amount": 10000,
        "account": "Debtors - EHH"
    })
    pos.hotel_room = "1001"
    pos.insert(ignore_permissions=True)
    pos.submit()
    print(f"Created POS Invoice: {pos.name}")

    # Check if redirect entry exists
    redirect_gles = frappe.db.get_all("GL Entry",
        filters={"voucher_no": pos.name, "remarks": ["like", "%Deferring Income%"]},
        fields=["account", "debit", "credit"]
    )
    print(f"Redirect GL Entries for POS: {redirect_gles}")

    # Check if Folio Transaction was created and NO GL entries for it
    folio_txn = frappe.db.get_value("Folio Transaction", 
        {"reference_name": pos.name}, "name"
    )
    print(f"Linked Folio Transaction: {folio_txn}")
    
    if folio_txn:
        folio_txn_gles = frappe.db.get_all("GL Entry",
            filters={"remarks": ["like", f"%Ref: {folio_txn}%"]},
            fields=["name"]
        )
        print(f"GL Entries for POS Folio Txn (Should be empty): {folio_txn_gles}")

    # Cleanup
    # frappe.db.rollback() 
    # Use rollback during dev to keep DB clean, but for verification we might want to see it in DB.
    # I'll leave it for now.

if __name__ == "__main__":
    verify_accounting()
