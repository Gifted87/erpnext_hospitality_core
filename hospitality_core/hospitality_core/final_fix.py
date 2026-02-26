import frappe
from frappe.utils import add_days, getdate, flt

def run_final_migration():
    print("\n" + "="*70)
    print("UNIFIED CLEANUP & MIGRATION V3 (Jan 16-20)")
    print("="*70 + "\n")
    
    guest_name = "Historical Migration Sync"
    customer_name = "Historical Migration Sync"
    
    # 1. CLEAN SWEEP
    print("1. Performing Clean Sweep...")
    # Delete Payment Entries
    pes = frappe.get_all("Payment Entry", filters={"party": customer_name}, fields=["name", "docstatus"])
    for pe in pes:
        if pe.docstatus == 1:
            frappe.get_doc("Payment Entry", pe.name).cancel()
        frappe.delete_doc("Payment Entry", pe.name, force=True)
        
    # Delete Reservations & Folios & GL Entries
    res = frappe.get_all("Hotel Reservation", filters={"guest": guest_name})
    for r in res:
        folio = frappe.db.get_value("Hotel Reservation", r.name, "folio")
        if folio:
            frappe.db.sql("DELETE FROM `tabFolio Transaction` WHERE parent = %s", (folio,))
            # Delete GL Entries for this folio
            frappe.db.sql("DELETE FROM `tabGL Entry` WHERE voucher_no = %s", (folio,))
            frappe.db.sql("DELETE FROM `tabGuest Folio` WHERE name = %s", (folio,))
        frappe.delete_doc("Hotel Reservation", r.name, force=True)

    # Cleanup any orphaned GLs for the range
    frappe.db.sql("""
        DELETE FROM `tabGL Entry` 
        WHERE posting_date BETWEEN '2026-01-16' AND '2026-01-21'
        AND (remarks LIKE 'Historical%%' OR remarks LIKE 'Ref: %%' OR remarks LIKE 'Income Realization%%')
    """)
    
    frappe.db.commit()
    print("Sweep Complete.")

    # 2. MIGRATION
    data = [
        {"date": "2026-01-16", "checkins": 36, "retained": 70, "sales": 6731000.00, "payments": 4987600.00},
        {"date": "2026-01-17", "checkins": 26, "retained": 75, "sales": 6694100.00, "payments": 5010010.00},
        {"date": "2026-01-18", "checkins": 24, "retained": 76, "sales": 7004600.00, "payments": 2753900.00},
        {"date": "2026-01-19", "checkins": 13, "retained": 52, "sales": 4606400.00, "payments": 1726800.00},
        {"date": "2026-01-20", "checkins": 7, "retained": 35, "sales": 2774500.00, "payments": 3515200.00},
    ]

    room_id = "1007"
    room_type = "Classic Deluxe"
    reception = "New Building"
    cash_account = "Cash - EHH"
    debtors_account = "Debtors - EHH"
    
    # Ensure Guest exists
    if not frappe.db.exists("Guest", guest_name):
        g = frappe.new_doc("Guest")
        g.full_name = guest_name
        g.guest_type = "Regular"
        g.insert(ignore_permissions=True)
        customer_id = g.customer
    else:
        customer_id = frappe.db.get_value("Guest", guest_name, "customer")

    active_reservations = []

    for day in data:
        p_date = day["date"]
        print(f"\n--- {p_date} ---")
        
        # Room management
        target_retained = day["retained"]
        current = len(active_reservations)
        if current < target_retained:
            for i in range(target_retained - current):
                res = frappe.new_doc("Hotel Reservation")
                res.guest = guest_name
                res.room = room_id
                res.room_type = room_type
                res.arrival_date = add_days(p_date, -1)
                res.departure_date = add_days(p_date, 1)
                res.status = "Checked Out"
                res.hotel_reception = reception
                res.insert(ignore_permissions=True, ignore_mandatory=True)
                active_reservations.append(res.name)
        elif current > target_retained:
            for i in range(current - target_retained):
                res_name = active_reservations.pop(0)
                frappe.db.set_value("Hotel Reservation", res_name, "departure_date", p_date)

        for i in range(day["checkins"]):
            res = frappe.new_doc("Hotel Reservation")
            res.guest = guest_name
            res.room = room_id
            res.room_type = room_type
            res.arrival_date = p_date
            res.departure_date = add_days(p_date, 1)
            res.status = "Checked Out"
            res.hotel_reception = reception
            res.insert(ignore_permissions=True, ignore_mandatory=True)
            active_reservations.append(res.name)

        # Financials on MASTER reservation of the day
        if active_reservations:
            # We always use the same "Master" reservation for the day's financials
            master_res_name = active_reservations[-1] # The last one checked in today
            folio_id = frappe.db.get_value("Hotel Reservation", master_res_name, "folio")
            
            if folio_id:
                # 1. Add REVENUE directly to Folio Transaction Table
                if day["sales"] > 0:
                    txn = frappe.get_doc({
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
                    txn.insert(ignore_permissions=True)
                    # GL Entries
                    from hospitality_core.hospitality_core.api.accounting import make_gl_entries_for_folio_transaction
                    make_gl_entries_for_folio_transaction(txn)
                    print(f"  Sales Added: {day['sales']}")

                # 2. Add PAYMENT via Payment Entry
                if day["payments"] > 0:
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
                        "hotel_reception": reception
                    })
                    pe.insert(ignore_permissions=True, ignore_mandatory=True)
                    pe.submit()
                    print(f"  Payment Added: {day['payments']}")

                # 3. Finalize Folio
                from hospitality_core.hospitality_core.api.folio import sync_folio_balance
                folio_doc = frappe.get_doc("Guest Folio", folio_id)
                sync_folio_balance(folio_doc)
                
                # Use direct DB update for status to avoid timestamp conflicts during migration
                frappe.db.set_value("Guest Folio", folio_id, {
                    "status": "Closed",
                    "close_date": p_date
                })
        
        frappe.db.commit()
        print(f"  ✔ Done {p_date}")

    print("\n" + "="*70)
    print("MIGRATION V3 COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_final_migration()
