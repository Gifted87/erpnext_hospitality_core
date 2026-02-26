import frappe

@frappe.whitelist()
def get_room_statuses():
    return frappe.get_all("Hotel Room", 
        fields=["name", "room_number", "status", "room_type"],
        filters={"is_enabled": 1},
        order_by="room_number asc"
    )

@frappe.whitelist()
def set_room_status(room, status):
    # Security check: Ensure user is Housekeeping or Manager
    if not frappe.has_permission("Hotel Room", "write"):
        frappe.throw("Not authorized to change room status")
    
    # If marking as "Available" (Clean), checking if there is still an active guest
    if status == "Available":
        active_res = frappe.db.exists("Hotel Reservation", {
            "room": room,
            "status": "Checked In"
        })
        if active_res:
            # Guest is still here, so status should be Occupied, not Available
            status = "Occupied"

    frappe.db.set_value("Hotel Room", room, "status", status)
    return True