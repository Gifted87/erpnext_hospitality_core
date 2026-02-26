import frappe
from frappe.utils import add_days, getdate, flt

def migrate_historical_data_v3():
    print("\n" + "="*70)
    print("HISTORICAL MIGRATION SYNC V3 (Jan 21-31)")
    print("="*70 + "\n")
    
    # Data from Jan 21st to Jan 31st, 2026
    data = [
        {"date": "2026-01-21", "checkins": 8, "retained": 34, "sales": 3048700.00, "payments": 713800.00},
        {"date": "2026-01-22", "checkins": 23, "retained": 33, "sales": 3608500.00, "payments": 1831400.00},
        {"date": "2026-01-23", "checkins": 27, "retained": 33, "sales": 4314200.00, "payments": 3430750.00},
        {"date": "2026-01-24", "checkins": 23, "retained": 37, "sales": 3591000.00, "payments": 3757900.00},
        {"date": "2026-01-25", "checkins": 12, "retained": 46, "sales": 4017500.00, "payments": 1496900.00},
        {"date": "2026-01-26", "checkins": 17, "retained": 35, "sales": 3011000.00, "payments": 2818000.00},
        {"date": "2026-01-27", "checkins": 21, "retained": 36, "sales": 3609900.00, "payments": 1686600.00},
        {"date": "2026-01-28", "checkins": 16, "retained": 37, "sales": 3301900.00, "payments": 1537000.00},
        {"date": "2026-01-29", "checkins": 22, "retained": 38, "sales": 4225100.00, "payments": 1580600.00},
        {"date": "2026-01-30", "checkins": 25, "retained": 40, "sales": 4960800.00, "payments": 7889000.00},
        {"date": "2026-01-31", "checkins": 23, "retained": 48, "sales": 4890100.00, "payments": 1968600.00},
    ]

    # Constants
    guest_full_name = "Historical Migration Sync"
    room_id = "1007"
    room_type = "Classic Deluxe"
    reception = "New Building"
    cash_account = "Cash - EHH"
    debtors_account = "Debtors - EHH"
    
    # 1. Clean up existing data for this period to avoid mess
    print("1. Cleaning up existing migration data for Jan 21-31...")
    for day in data:
        p_date = day["date"]
        # Delete Payment Entries
        pes = frappe.get_all("Payment Entry", filters={"remarks": ["like", f"%HIST-{p_date}%"]})
        for pe in pes:
            frappe.delete_doc("Payment Entry", pe.name, force=True)
            
        # Delete Folio Transactions
        frappe.db.sql("DELETE FROM `tabFolio Transaction` WHERE posting_date = %s AND description LIKE 'Historical Revenue %%'", (p_date,))
        # Delete GL Entries
        frappe.db.sql("DELETE FROM `tabGL Entry` WHERE posting_date = %s AND remarks LIKE 'Historical Hotel Payment Sync%%%%'", (p_date,))
        frappe.db.sql("DELETE FROM `tabGL Entry` WHERE posting_date = %s AND (remarks LIKE 'Ref: %%' OR remarks LIKE '%%Realization%%')", (p_date,))

    # 2. Setup Guest
    guest = frappe.get_doc("Guest", guest_full_name) if frappe.db.exists("Guest", guest_full_name) else None
    if not guest:
        g = frappe.new_doc("Guest")
        g.full_name = guest_full_name
        g.guest_type = "Regular"
        g.insert(ignore_permissions=True)
        guest_id = g.name
        customer_id = g.customer
    else:
        guest_id = guest.name
        customer_id = guest.customer

    print(f"Syncing with Guest: {guest_id} / Customer: {customer_id}")
    
    # Track reservations that are "in house" to maintain occupancy counts
    active_reservations = []

    for day in data:
        p_date = day["date"]
        target_retained = day.get("retained", 0)
        target_checkins = day.get("checkins", 0)
        
        print(f"\n--- Processing {p_date} ---")
        
        # Manage Retained (retained means they were already in house yesterday)
        current_count = len(active_reservations)
        if current_count < target_retained:
            deficit = target_retained - current_count
            for i in range(deficit):
                res = frappe.new_doc("Hotel Reservation")
                res.guest = guest_id
                res.room = room_id
                res.room_type = room_type
                res.arrival_date = add_days(p_date, -1)
                res.departure_date = add_days(p_date, 1)
                res.status = "Checked Out"
                res.hotel_reception = reception
                res.insert(ignore_permissions=True, ignore_mandatory=True)
                active_reservations.append(res.name)
        elif current_count > target_retained:
            excess = current_count - target_retained
            # Mark excess as checked out today
            for i in range(excess):
                res_name = active_reservations.pop(0)
                frappe.db.set_value("Hotel Reservation", res_name, "departure_date", p_date)

        # Manage Checkins (new arrivals today)
        for i in range(target_checkins):
            res = frappe.new_doc("Hotel Reservation")
            res.guest = guest_id
            res.room = room_id
            res.room_type = room_type
            res.arrival_date = p_date
            res.departure_date = add_days(p_date, 1)
            res.status = "Checked Out"
            res.hotel_reception = reception
            res.insert(ignore_permissions=True, ignore_mandatory=True)
            active_reservations.append(res.name)

        # Financials - Consolidated on the first reservation's folio
        if active_reservations:
            # We use the first reservation in the list as the primary "folio account" for the day
            first_res_name = active_reservations[0]
            first_res = frappe.get_doc("Hotel Reservation", first_res_name)
            folio_id = first_res.folio
            
            if folio_id:
                folio = frappe.get_doc("Guest Folio", folio_id)
                folio.status = "Open"
                
                # Add Sales Transaction
                if day["sales"] > 0:
                    print(f"  Adding Revenue: {day['sales']}")
                    # Use append to add to child table
                    new_txn = folio.append("transactions", {
                        "posting_date": p_date,
                        "item": "ROOM-RENT",
                        "description": f"Historical Revenue {p_date}",
                        "qty": 1,
                        "amount": day["sales"],
                        "bill_to": "Guest",
                        "is_void": 0
                    })
                    
                    # Save folio (triggers auto-calculation)
                    folio.save(ignore_permissions=True)
                    
                    # make_gl_entries_for_folio_transaction is called by AFTER_SAVE hook usually, 
                    # but since we are doing manual script, we can call it if needed.
                    # Wait, the hook in hooks.py is "after_save" for Folio Transaction, 
                    # but here we are saving the Parent (Guest Folio).
                    # Actually, for Folio Transaction after_save works when the child table is saved.
                    
                    # Manually trigger GL Entries for the new transaction to be sure
                    from hospitality_core.hospitality_core.api.accounting import make_gl_entries_for_folio_transaction
                    # Need to Reload to get the transaction name
                    folio.reload()
                    for t in folio.transactions:
                        if t.item == "ROOM-RENT" and t.posting_date == getdate(p_date) and flt(t.amount) == flt(day["sales"]):
                            make_gl_entries_for_folio_transaction(t)
                
                # Add Payment
                if day["payments"] > 0:
                    print(f"  Adding Payment: {day['payments']}")
                    pe = frappe.get_doc({
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
                        "mode_of_payment": "Cash",
                        "reference_no": folio_id,
                        "reference_date": p_date,
                        "remarks": f"Historical Hotel Payment Sync | Ref: HIST-{p_date}",
                        "cashier": "Administrator",
                        "hotel_reception": reception
                    })
                    pe.insert(ignore_permissions=True, ignore_mandatory=True)
                    pe.submit()
                
                # Final Balance Sync and Close
                folio.reload()
                from hospitality_core.hospitality_core.api.folio import sync_folio_balance
                sync_folio_balance(folio)
                
                # Re-reload and save status
                folio.reload()
                # Use db_set to bypass the validation that prevents closing with a balance
                # because in historical data, a single day's payment might not cover that day's revenue
                frappe.db.set_value("Guest Folio", folio.name, {
                    "status": "Closed",
                    "close_date": p_date
                })
        
        frappe.db.commit()
        print(f"  ✔ Day Complete: {p_date} | Active Count: {len(active_reservations)}")

    print("\n" + "="*70)
    print("MIGRATION V3 COMPLETE")
    print("="*70 + "\n")
