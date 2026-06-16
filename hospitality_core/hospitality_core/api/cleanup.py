import frappe

@frappe.whitelist()
def clear_reservations():
    # 1. Clear Hotel Reservations and child tables
    print("Clearing Hotel Reservations...")
    try:
        res_count = frappe.db.count("Hotel Reservation")
        frappe.db.delete("Hotel Reservation")
        frappe.db.sql("DELETE FROM `tabReservation Routing`", ignore_ddl=True)
        print(f"✔ Deleted {res_count} Hotel Reservations.")
    except Exception as e:
        print(f"✘ Error clearing Hotel Reservations: {e}")

    # 2. Clear Group Bookings and child tables
    print("Clearing Group Bookings...")
    try:
        gb_count = frappe.db.count("Hotel Group Booking")
        frappe.db.delete("Hotel Group Booking")
        frappe.db.sql("DELETE FROM `tabHotel Group Booking Room`", ignore_ddl=True)
        print(f"✔ Deleted {gb_count} Group Bookings.")
    except Exception as e:
        print(f"✘ Error clearing Group Bookings: {e}")

    # 3. Reset Room Statuses
    print("Resetting Room Statuses to Available...")
    try:
        frappe.db.sql("UPDATE `tabHotel Room` SET status = 'Available'")
        print("✔ Room statuses reset.")
    except Exception as e:
        print(f"✘ Could not reset rooms: {e}")

    frappe.db.commit()
    print("--- Reservation Deletion Complete ---")
