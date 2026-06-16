import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def sync_room_status():
    """
    Authoritative room status reconciliation.

    Rules:
      - Rooms with an active 'Checked In' reservation → Occupied
      - Rooms with a 'Reserved' reservation arriving today → Occupied
      - Rooms marked 'Out of Order' → left unchanged (managed manually)
      - All other rooms → Available
    """
    today = nowdate()
    print(f"\nStarting Room Status Sync for {today}...")

    rooms = frappe.get_all("Hotel Room", fields=["name", "status"])
    print(f"Found {len(rooms)} rooms.")

    # Build sets for fast lookup
    checked_in_rooms = set(frappe.db.sql("""
        SELECT DISTINCT room FROM `tabHotel Reservation`
        WHERE status = 'Checked In' AND room IS NOT NULL
    """, as_list=True, flat=True))

    arriving_today_rooms = set(frappe.db.sql("""
        SELECT DISTINCT room FROM `tabHotel Reservation`
        WHERE status = 'Reserved' AND arrival_date = %s AND room IS NOT NULL
    """, (today,), as_list=True, flat=True))

    occupied_rooms = checked_in_rooms | arriving_today_rooms

    updated_count = 0
    for room in rooms:
        # Never touch Out of Order rooms
        if room.status == "Out of Order":
            continue

        expected_status = "Occupied" if room.name in occupied_rooms else "Available"

        if room.status != expected_status:
            print(f"  {room.name}: {room.status} → {expected_status}")
            frappe.db.set_value("Hotel Room", room.name, "status", expected_status)
            updated_count += 1

    frappe.db.commit()
    print(f"\nSync complete. Updated {updated_count} room(s).")
    return {"updated": updated_count}
