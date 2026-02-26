import frappe
from frappe.utils import add_days

def migrate_historical_data():
    # Data from Jan 1st to Jan 15th, 2026
    data = [
        {"date": "2026-01-01", "occupied": 55, "sales": 2505000.00, "payments": 2206000.00},
        {"date": "2026-01-02", "occupied": 43, "sales": 2245000.00, "payments": 1490200.00},
        {"date": "2026-01-03", "occupied": 34, "sales": 1675000.00, "payments": 1781900.00},
        {"date": "2026-01-04", "occupied": 52, "sales": 2315000.00, "payments": 1627400.00},
        {"date": "2026-01-05", "occupied": 45, "sales": 2030000.00, "payments": 2220800.00},
        {"date": "2026-01-06", "occupied": 53, "sales": 2430000.00, "payments": 2135000.00},
        {"date": "2026-01-07", "occupied": 52, "sales": 2465000.00, "payments": 2117100.00},
        {"date": "2026-01-08", "occupied": 50, "sales": 2245000.00, "payments": 1336700.00},
        {"date": "2026-01-09", "occupied": 69, "sales": 3200000.00, "payments": 3149300.00},
        {"date": "2026-01-10", "occupied": 73, "sales": 3080000.00, "payments": 2652400.00},
        {"date": "2026-01-11", "occupied": 85, "sales": 3755000.00, "payments": 3054200.00},
        {"date": "2026-01-12", "occupied": 62, "sales": 2720000.00, "payments": 3648310.00},
        {"date": "2026-01-13", "occupied": 60, "sales": 2840000.00, "payments": 5306500.00},
        {"date": "2026-01-14", "occupied": 70, "sales": 3200000.00, "payments": 2117700.00},
        {"date": "2026-01-15", "occupied": 85, "sales": 3790000.00, "payments": 3087200.00},
    ]

    # Setup Constants
    guest_full_name = "Historical Migration Sync"
    room_id = "1007"
    room_type = "Classic Deluxe"
    reception = "New Building"
    cash_account = "Cash - EHH"
    debtors_account = "Debtors - EHH"
    company_name = "Edo Heritage Hotel"

    # 1. Create/Get Guest
    existing_guest = frappe.db.get_value("Guest", {"full_name": guest_full_name}, "name")
    if not existing_guest:
        g = frappe.new_doc("Guest")
        g.full_name = guest_full_name
        g.guest_type = "Regular"
        g.insert(ignore_permissions=True)
        guest_id = g.name
        customer_id = g.customer
    else:
        guest_id = existing_guest
        customer_id = frappe.db.get_value("Guest", guest_id, "customer")

    print(f"Syncing data with Guest: {guest_id}...")

    for day in data:
        p_date = day["date"]
        
        # Avoid duplicates
        if frappe.db.exists("Payment Entry", {"reference_no": f"HIST-{p_date}"}):
            print(f"Skipping {p_date} (Already synced)")
            continue

        # 2. Create 'Ghost' Reservations for Occupancy Reports
        # We create multiple reservations to fill up the 'Occupied' count for the day
        res_names = []
        for i in range(day["occupied"]):
            res = frappe.new_doc("Hotel Reservation")
            res.guest = guest_id
            res.room = room_id
            res.room_type = room_type
            res.arrival_date = p_date
            res.departure_date = add_days(p_date, 1)
            res.status = "Checked Out" # Important for reports
            res.hotel_reception = reception
            res.is_company_guest = 0
            res.insert(ignore_permissions=True, ignore_mandatory=True)
            res_names.append(res.name)

        # 3. Handle Revenue (Post all revenue to the first reservation's folio)
        first_res = frappe.get_doc("Hotel Reservation", res_names[0])
        folio_id = first_res.folio
        
        if folio_id:
            # Set Folio to Open to allow adding transactions
            frappe.db.set_value("Guest Folio", folio_id, "status", "Open")
            
            # Post Revenue Transaction
            ft = frappe.get_doc({
                "doctype": "Folio Transaction",
                "parent": folio_id,
                "parenttype": "Guest Folio",
                "parentfield": "transactions",
                "posting_date": p_date,
                "item": "ROOM-RENT",
                "description": f"Historical Revenue Sync {p_date}",
                "qty": 1,
                "amount": day["sales"],
                "bill_to": "Guest",
                "is_void": 0
            })
            ft.insert(ignore_permissions=True)
            
            # Close Folio
            frappe.db.set_value("Guest Folio", folio_id, {"status": "Closed", "close_date": p_date})

        # 4. Create Payment Entry for daily totals
        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = "Receive"
        pe.party_type = "Customer"
        pe.party = customer_id
        pe.posting_date = p_date
        pe.paid_from = debtors_account
        pe.paid_to = cash_account
        pe.paid_amount = day["payments"]
        pe.received_amount = day["payments"]
        pe.target_exchange_rate = 1
        pe.mode_of_payment = "Cash"
        pe.reference_no = f"HIST-{p_date}"
        pe.insert(ignore_permissions=True)
        pe.submit()

        print(f"✔ Done: {p_date} | {day['occupied']} Rooms | {day['sales']} Sales | {day['payments']} Paid")
        frappe.db.commit()

    print("--- FULL MIGRATION SYNC COMPLETE ---")
