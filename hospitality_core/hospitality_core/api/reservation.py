import frappe
from frappe import _
from frappe.utils import getdate, date_diff, nowdate

def check_availability(room, arrival_date, departure_date, ignore_reservation=None):
    """
    Checks if a room is available for the given date range.
    Returns True if available, raises ValidationError if not.
    """
    if not room or not arrival_date or not departure_date:
        return

    # 1. Check if Room is Enabled (Maintenance check)
    room_status = frappe.db.get_value("Hotel Room", room, ["status", "is_enabled"], as_dict=True)
    if not room_status.is_enabled:
        frappe.throw(_("Room {0} is currently disabled/under maintenance.").format(room))
    
    if room_status.status == "Out of Order":
        frappe.throw(_("Room {0} is marked Out of Order.").format(room))

    # 2. Check Overlapping Reservations
    # Logic: New Arrival < Existing Departure AND New Departure > Existing Arrival
    filters = {
        "room": room,
        "status": ["in", ["Reserved", "Checked In"]],
        "name": ["!=", ignore_reservation] if ignore_reservation else ["is", "set"]
    }
    
    existing_bookings = frappe.get_all("Hotel Reservation", 
        filters=filters,
        fields=["name", "arrival_date", "departure_date", "guest"]
    )

    for booking in existing_bookings:
        # Check for date overlap
        if (getdate(arrival_date) < getdate(booking.departure_date)) and \
           (getdate(departure_date) > getdate(booking.arrival_date)):
             frappe.throw(
                _("Room {0} is already booked by {1} from {2} to {3} (Reservation: {4})").format(
                    room, booking.guest, booking.arrival_date, booking.departure_date, booking.name
                )
             )
    
    return True

def check_bulk_availability(rooms, arrival_date, departure_date, ignore_reservation=None):
    """
    Checks if a list of rooms is available for the given date range.
    Collects ALL conflicts and raises a single ValidationError.
    """
    if not rooms or not arrival_date or not departure_date:
        return

    conflicts = []

    # 1. Check Room Maintenance Status for all rooms in batch
    room_data = frappe.get_all("Hotel Room", 
        filters={"room_number": ["in", rooms]},
        fields=["room_number", "status", "is_enabled"]
    )
    
    room_map = {r.room_number: r for r in room_data}

    for room_num in rooms:
        r = room_map.get(room_num)
        if not r:
            conflicts.append(_("Room {0} does not exist.").format(room_num))
            continue
            
        if not r.is_enabled:
            conflicts.append(_("Room {0} is currently disabled/under maintenance.").format(room_num))
        elif r.status == "Out of Order":
            conflicts.append(_("Room {0} is marked Out of Order.").format(room_num))

    # 2. Check Overlapping Reservations for all rooms in batch
    # Logic: New Arrival < Existing Departure AND New Departure > Existing Arrival
    existing_bookings = frappe.get_all("Hotel Reservation", 
        filters={
            "room": ["in", rooms],
            "status": ["in", ["Reserved", "Checked In"]],
            "name": ["!=", ignore_reservation] if ignore_reservation else ["is", "set"]
        },
        fields=["name", "arrival_date", "departure_date", "guest", "room"]
    )

    for booking in existing_bookings:
        # Check for date overlap
        if (getdate(arrival_date) < getdate(booking.departure_date)) and \
           (getdate(departure_date) > getdate(booking.arrival_date)):
             conflicts.append(
                _("Room {0} is already booked by {1} from {2} to {3} (Reservation: {4})").format(
                    booking.room, booking.guest, booking.arrival_date, booking.departure_date, booking.name
                )
             )

    if conflicts:
        message = _("The following availability issues were found:") + "<br><br>"
        message += "<div class='alert alert-danger'>"
        message += "<ul>"
        for conflict in conflicts:
            message += f"<li>{conflict}</li>"
        message += "</ul>"
        message += "</div>"
        frappe.throw(message, title=_("Room Availability Conflict"))

    return True

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_available_rooms_for_picker(doctype, txt, searchfield, start, page_len, filters):
    """
    Search picker for rooms that are available for the selected dates.
    Filters: arrival_date, departure_date, room_type, ignore_reservation
    """
    filters = frappe.parse_json(filters)
    arrival = filters.get("arrival_date")
    departure = filters.get("departure_date")
    room_type = filters.get("room_type")
    ignore = filters.get("ignore_reservation")

    if not arrival or not departure:
        # If dates aren't set, return all rooms of that type (or all if no type)
        return frappe.db.sql("""
            SELECT name, room_type, status
            FROM `tabHotel Room`
            WHERE is_enabled = 1
            AND (%s IS NULL OR room_type = %s)
            AND name LIKE %s
            ORDER BY name ASC
            LIMIT %s, %s
        """, (room_type, room_type, f"%{txt}%", start, page_len))

    # Complex Query: Find rooms that are NOT in the overlapping reservations set
    return frappe.db.sql("""
        SELECT name, room_type, status
        FROM `tabHotel Room`
        WHERE is_enabled = 1
        AND status != 'Out of Order'
        AND (%s IS NULL OR room_type = %s)
        AND name LIKE %s
        AND name NOT IN (
            SELECT room FROM `tabHotel Reservation`
            WHERE status IN ('Reserved', 'Checked In')
            AND name != %s
            AND arrival_date < %s
            AND departure_date > %s
        )
        ORDER BY name ASC
        LIMIT %s, %s
    """, (room_type, room_type, f"%{txt}%", ignore or "", departure, arrival, start, page_len))

def create_folio(reservation_doc):
    """
    Creates a 'Provisional' Guest Folio linked to this reservation.
    """
    if frappe.db.exists("Guest Folio", {"reservation": reservation_doc.name, "status": ["!=", "Cancelled"]}):
        return

    folio = frappe.new_doc("Guest Folio")
    folio.guest = reservation_doc.guest
    folio.reservation = reservation_doc.name
    folio.room = reservation_doc.room
    folio.status = "Provisional"
    folio.company = reservation_doc.company # If corporate booking
    folio.hotel_reception = reservation_doc.hotel_reception
    folio.reserved_by = reservation_doc.reserved_by
    folio.open_date = nowdate()
    
    # Save the Folio
    folio.insert(ignore_permissions=True)
    
    # Link Folio back to Reservation
    reservation_doc.db_set("folio", folio.name)
    frappe.msgprint(_("Guest Folio {0} created successfully.").format(folio.name))

    # Transfer existing balances from the Guest Balance Ledger
    from hospitality_core.hospitality_core.api.folio import transfer_existing_balances
    transfer_existing_balances(folio)

@frappe.whitelist()
def get_room_rate(room=None, rate_plan=None, room_type=None, arrival_date=None,
                  discount_type=None, discount_value=None, is_complimentary=None):
    """
    Returns the base rate and discounted rate for the reservation form preview.
    Called by hotel_reservation.js when room, rate_plan, or discount fields change.
    """
    from hospitality_core.hospitality_core.api.night_audit import get_rate
    from frappe.utils import flt, nowdate

    # Resolve room_type from room if not provided
    if room and not room_type:
        room_type = frappe.db.get_value("Hotel Room", room, "room_type")

    if not room_type:
        return {"base_rate": 0, "discount_amount": 0, "final_rate": 0}

    date = arrival_date or nowdate()
    base_rate = flt(get_rate(rate_plan, room_type, date))

    # Calculate discount
    discount_amount = 0.0
    if frappe.utils.cint(is_complimentary):
        discount_amount = base_rate
    elif discount_type == "Percentage":
        discount_amount = base_rate * (flt(discount_value) / 100.0)
    elif discount_type == "Amount":
        discount_amount = flt(discount_value)

    final_rate = base_rate - discount_amount

    return {
        "base_rate": base_rate,
        "discount_amount": discount_amount,
        "final_rate": final_rate
    }