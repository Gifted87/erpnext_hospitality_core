import frappe
from frappe import _
from hospitality_core.hospitality_core.api.reservation import check_availability

@frappe.whitelist()
def process_room_move(reservation_name, new_room):
    """
    Moves a checked-in guest to a new room.
    1. Validate permissions.
    2. Validate New Room availability.
    3. Mark Old Room 'Dirty'.
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

    # 1. Validate Availability (for the remaining dates)
    # We check from Today to Departure Date
    check_availability(new_room, frappe.utils.nowdate(), res.departure_date, ignore_reservation=res.name)

    # 2. Update Statuses
    # Old Room -> Dirty
    frappe.db.set_value("Hotel Room", old_room, "status", "Dirty")
    
    # New Room -> Occupied
    frappe.db.set_value("Hotel Room", new_room, "status", "Occupied")

    # 3. Update Documents (Bypass set_only_once restriction)
    res.db_set("room", new_room)
    
    # Update Folio
    if res.folio:
        frappe.db.set_value("Guest Folio", res.folio, "room", new_room)

    # 4. Log the Move (Optional: Add a comment)
    res.add_comment("Info", _("Moved from Room {0} to Room {1} on {2}").format(
        old_room, new_room, frappe.utils.now_datetime()
    ))
    
    frappe.msgprint(_("Successfully moved guest to Room {0}").format(new_room))
    
    return True