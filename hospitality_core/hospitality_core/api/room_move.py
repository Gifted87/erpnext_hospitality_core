import frappe
from frappe import _
from hospitality_core.hospitality_core.api.reservation import check_availability

@frappe.whitelist()
def process_room_move(reservation_name, new_room):
    """
    Moves a checked-in guest to a new room.
    1. Validate permissions.
    2. Validate New Room availability.
    3. Mark Old Room 'Available'.
    4. Mark New Room 'Occupied'.
    5. Update Reservation and Folio.
    """
    
    if not ("Frontdesk Supervisor" in frappe.get_roles() or frappe.session.user == "Administrator"):
        frappe.throw(_("Access Denied. Only Frontdesk Supervisors can move rooms."))

    res = frappe.get_doc("Hotel Reservation", reservation_name)
    
    if res.status != "Checked In":
        frappe.throw(_("Room moves are only allowed for Checked In guests."))
        
    if res.room == new_room:
        frappe.throw(_("New Room cannot be the same as Current Room."))

    old_room = res.room
    new_room_type = frappe.db.get_value("Hotel Room", new_room, "room_type")

    # 1. Validate Availability (for the remaining dates)
    # We check from Today to Departure Date
    check_availability(new_room, frappe.utils.nowdate(), res.departure_date, ignore_reservation=res.name)

    # 2. Update Statuses
    # Old Room -> Available (housekeeping can manually mark Dirty if needed)
    frappe.db.set_value("Hotel Room", old_room, "status", "Available")
    
    # New Room -> Occupied
    frappe.db.set_value("Hotel Room", new_room, "status", "Occupied")

    # 3. Update Documents (Bypass set_only_once restriction)
    res.db_set("room", new_room)
    if new_room_type and res.room_type != new_room_type:
        res.db_set("room_type", new_room_type)
    
    # Update Folio
    if res.folio:
        frappe.db.set_value("Guest Folio", res.folio, "room", new_room)

    # 4. Log the Move (Optional: Add a comment)
    res.add_comment("Info", _("Moved from Room {0} to Room {1} on {2}").format(
        old_room, new_room, frappe.utils.now_datetime()
    ))
    
    frappe.msgprint(_("Successfully moved guest to Room {0}").format(new_room))
    
    return True