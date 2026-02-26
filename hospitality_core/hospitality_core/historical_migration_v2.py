import frappe
from frappe.utils import add_days, getdate, flt

def migrate_historical_data_v2():
    print("\n" + "="*70)
    print("HISTORICAL MIGRATION SYNC V2 (Jan 16-20)")
    print("="*70 + "\n")
    
    # Data from Jan 16th to Jan 20th, 2026
    data = [
        {"date": "2026-01-16", "checkins": 36, "retained": 70, "sales": 6731000.00, "payments": 4987600.00},
        {"date": "2026-01-17", "checkins": 26, "retained": 75, "sales": 6694100.00, "payments": 5010010.00},
        {"date": "2026-01-18", "checkins": 24, "retained": 76, "sales": 7004600.00, "payments": 2753900.00},
        {"date": "2026-01-19", "checkins": 13, "retained": 52, "sales": 4606400.00, "payments": 1726800.00},
        {"date": "2026-01-20", "checkins": 7, "retained": 35, "sales": 2774500.00, "payments": 3515200.00},
    ]

    # Constants
    guest_full_name = "Historical Migration Sync"
    room_id = "1007"
    room_type = "Classic Deluxe"
    reception = "New Building"
    cash_account = "Cash - EHH"
    debtors_account = "Debtors - EHH"
    
    # 1. Clean up existing data for this period to avoid mess
    print("1. Cleaning up existing migration data for Jan 16-20...")
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
        frappe.db.sql("DELETE FROM `tabGL Entry` WHERE posting_date = %s AND remarks LIKE 'Ref: %%'", (p_date,))

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
    
    active_reservations = []

    for day in data:
        p_date = day["date"]
        target_retained = day.get("retained", 0)
        target_checkins = day.get("checkins", 0)
        
        print(f"\n--- Processing {p_date} ---")
        
        # Manage Retained
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

        # Manage Checkins
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
            first_res_name = active_reservations[0]
            first_res = frappe.get_doc("Hotel Reservation", first_res_name)
            folio_id = first_res.folio
            
            if folio_id:
                folio = frappe.get_doc("Guest Folio", folio_id)
                folio.status = "Open"
                
                # Add Sales Transaction
                if day["sales"] > 0:
                    print(f"  Adding Revenue: {day['sales']}")
                    folio.append("transactions", {
                        "posting_date": p_date,
                        "item": "ROOM-RENT",
                        "description": f"Historical Revenue {p_date}",
                        "qty": 1,
                        "amount": day["sales"],
                        "bill_to": "Guest",
                        "is_void": 0
                    })
                
                # Save folio (triggers auto-calculation and updates child table parent fields)
                folio.reload() # Get latest timestamp in case hooks modified it
                folio.save(ignore_permissions=True)
                
                # Force GL Entries for revenue
                # We need the transaction name from the saved child table
                for t in folio.transactions:
                    if t.item == "ROOM-RENT" and t.posting_date == getdate(p_date) and t.amount == day["sales"]:
                        from hospitality_core.hospitality_core.api.accounting import make_gl_entries_for_folio_transaction
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
                        "paid_to": "Room Bookings - EHH", # This account is used for realization hook
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
                folio.status = "Closed"
                folio.close_date = p_date
                folio.save(ignore_permissions=True)
        
        frappe.db.commit()
        print(f"  ✔ Day Complete: {p_date} | Active Count: {len(active_reservations)}")

    print("\n" + "="*70)
    print("MIGRATION COMPLETE")
    print("="*70 + "\n")
