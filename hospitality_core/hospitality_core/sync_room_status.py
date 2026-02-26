import frappe

def sync_room_status():
    print("\nStarting Room Status Sync...")
    
    # Get all rooms
    rooms = frappe.get_all("Hotel Room", fields=["name", "status"])
    print(f"Found {len(rooms)} rooms.")
    
    updated_count = 0
    
    for room in rooms:
        # Check for active Checked In reservation
        # We look for reservations that are currently 'Checked In' linked to this room
        active_res = frappe.db.get_value("Hotel Reservation", {
            "room": room.name,
            "status": "Checked In"
        }, "name")
        
        expected_status = "Occupied" if active_res else "Available"
        
        # Check against "Unavailable" too just in case we need to fix previous runs
        if room.status != expected_status or room.status == "Unavailable":
            print(f"Updating {room.name}: {room.status} -> {expected_status} (Active Res: {active_res})")
            frappe.db.set_value("Hotel Room", room.name, "status", expected_status)
            updated_count += 1
            
    frappe.db.commit()
    print(f"\nSync Complete. Updated {updated_count} rooms.")

def main():
    sync_room_status()

if __name__ == "__main__":
    main()
