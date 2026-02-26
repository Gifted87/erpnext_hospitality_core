import frappe
from frappe.utils import add_days, getdate

def migrate_historical_data():
    import frappe
    from frappe.utils import add_days, getdate, flt
    
    # Data from Jan 16th to Jan 20th, 2026
    data = [
        {"date": "2026-01-16", "checkins": 36, "retained": 70, "sales": 6731000.00, "payments": 4987600.00},
        {"date": "2026-01-17", "checkins": 26, "retained": 75, "sales": 6694100.00, "payments": 5010010.00},
        {"date": "2026-01-18", "checkins": 24, "retained": 76, "sales": 7004600.00, "payments": 2753900.00},
        {"date": "2026-01-19", "checkins": 13, "retained": 52, "sales": 4606400.00, "payments": 1726800.00},
        {"date": "2026-01-20", "checkins": 7, "retained": 35, "sales": 2774500.00, "payments": 3515200.00},
    ]

    # Setup Constants
    guest_full_name = "Historical Migration Sync"
    room_id = "1007"
    room_type = "Classic Deluxe"
    reception = "New Building"
    cash_account = "Cash - EHH"
    debtors_account = "Debtors - EHH"
    
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
    
    # State tracking: List of reservation names currently 'in-house'
    # We maintain their 'planned departure date'.
    # But since we simulate day-by-day, we treat everyone in this list as currently checked in.
    # On each day, we decide who stays (extend departure) and who leaves (let expire).
    active_reservations = []

    for day in data:
        p_date = day["date"]
        target_retained = day.get("retained", 0)
        target_checkins = day.get("checkins", 0)
        
        # Step A: Manage Retained Guests
        # These are guests from 'active_reservations' that continue to stay.
        # We need exactly 'target_retained' count to stay.
        
        # If we have shortage (e.g. Day 1 retained guests presumed to be from before simulation)
        current_count = len(active_reservations)
        
        if current_count < target_retained:
            # We need to conjure guests from the past
            deficit = target_retained - current_count
            print(f"  Day {p_date}: Influx of {deficit} pre-existing retained guests.")
            for i in range(deficit):
                res = frappe.new_doc("Hotel Reservation")
                res.guest = guest_id
                res.room = room_id
                res.room_type = room_type
                res.arrival_date = add_days(p_date, -1) # Arrived yesterday (or earlier)
                res.departure_date = add_days(p_date, 1) # Stays until tomorrow
                res.status = "Checked Out" # Status for historical record
                res.hotel_reception = reception
                res.is_company_guest = 0
                res.insert(ignore_permissions=True, ignore_mandatory=True)
                active_reservations.append(res.name)
        
        elif current_count > target_retained:
            # We have too many potentials. Some must check out today.
            # We keep 'target_retained' number of guests.
            # The others (excess) are allowed to expire/checkout today (Departure=p_date).
            # But wait, my logic sets Dep=p_date+1 when creating/extending.
            # So if we don't touch them, they depart tomorrow?
            # We need to change their Departure to TODAY (p_date) so they are NOT retained tomorrow.
            excess = current_count - target_retained
            
            # Identify who leaves. We take from the front of the list (oldest?)
            leaving_guests = active_reservations[:excess]
            staying_guests = active_reservations[excess:]
            
            # For leaving guests, set Departure = Today
            for res_name in leaving_guests:
                 frappe.db.set_value("Hotel Reservation", res_name, "departure_date", p_date)
            
            # Update active list
            active_reservations = staying_guests
            
        # For the 'target_retained' guests staying, ensure their Departure is at least Tomorrow
        for res_name in active_reservations:
             # We extend them to Tomorrow (so they cover Today)
             frappe.db.set_value("Hotel Reservation", res_name, "departure_date", add_days(p_date, 1))

        # Step B: Manage New Check-ins
        # Create new records for today's arrivals
        for i in range(target_checkins):
            res = frappe.new_doc("Hotel Reservation")
            res.guest = guest_id
            res.room = room_id
            res.room_type = room_type
            res.arrival_date = p_date
            res.departure_date = add_days(p_date, 1) # Default 1 night, will extend if retained
            res.status = "Checked Out"
            res.hotel_reception = reception
            res.is_company_guest = 0
            res.insert(ignore_permissions=True, ignore_mandatory=True)
            active_reservations.append(res.name)

        # Step C: Financials
        # Link financials to the FIRST active reservation of the day (arbitrary)
        if active_reservations and not frappe.db.exists("Payment Entry", {"remarks": ["like", f"%HIST-{p_date}%"]}):
             first_res_name = active_reservations[0]
             folio_id = frappe.db.get_value("Hotel Reservation", first_res_name, "folio")
             
             if folio_id:
                  # Ensure folio is Open for posting
                  frappe.db.set_value("Guest Folio", folio_id, "status", "Open")
                  
                  # 1. Post Revenue (if any)
                  if day["sales"] > 0:
                       ft = frappe.get_doc({
                            "doctype": "Folio Transaction",
                            "parent": folio_id,
                            "parenttype": "Guest Folio",
                            "parentfield": "transactions",
                            "posting_date": p_date,
                            "item": "ROOM-RENT",
                            "description": f"Historical Revenue {p_date}",
                            "qty": 1,
                            "amount": day["sales"],
                            "bill_to": "Guest",
                            "is_void": 0
                       })
                       ft.insert(ignore_permissions=True)
                       
                       # Force creation of GL Entries for this transaction
                       # (In case .insert() on child doc doesn't trigger the hook)
                       from hospitality_core.hospitality_core.api.accounting import make_gl_entries_for_folio_transaction
                       make_gl_entries_for_folio_transaction(ft)


                  # 2. Post Payment (if any)
                  if day["payments"] > 0:
                       # The process_payment_entry hook will automatically create the Folio Transaction
                       # if reference_no = folio_id.
                       pe_dict = {
                          "doctype": "Payment Entry",
                          "payment_type": "Receive",
                          "party_type": "Customer",
                          "party": customer_id,
                          "posting_date": p_date,
                          "company": "Edo Heritage Hotel",
                          "cost_center": "Main - EHH",
                          "paid_from": debtors_account,
                          "paid_to": "Room Bookings - EHH",
                          "paid_amount": flt(day["payments"]),
                          "received_amount": flt(day["payments"]),
                          "source_exchange_rate": 1,
                          "target_exchange_rate": 1,
                          "mode_of_payment": "Cash",
                          "reference_no": folio_id, # Must match FOLIO- naming for hook and report
                          "reference_date": p_date,
                          "remarks": f"Historical Hotel Payment Sync | Ref: HIST-{p_date}",
                          "cashier": "Administrator",
                          "hotel_reception": reception
                       }
                       pe = frappe.get_doc(pe_dict)
                       pe.insert(ignore_permissions=True, ignore_mandatory=True)
                       pe.submit()

                  # 3. Final Sync and Close Folio
                  from hospitality_core.hospitality_core.api.folio import sync_folio_balance
                  sync_folio_balance(frappe.get_doc("Guest Folio", folio_id))
                  frappe.db.set_value("Guest Folio", folio_id, {"status": "Closed", "close_date": p_date})

        frappe.db.commit()
        print(f"✔ Done: {p_date} | Checkins: {target_checkins}, Retained: {target_retained} | Active: {len(active_reservations)}")

    print("--- FULL MIGRATION SYNC COMPLETE ---")
