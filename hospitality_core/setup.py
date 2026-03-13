import frappe
from frappe import _

def after_install():
    create_roles()
    create_custom_fields()
    create_default_data()

def create_roles():
    roles = ["Hospitality User", "Hospitality Manager", "Housekeeping Staff"]
    for role in roles:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert()

def create_custom_fields():
    # Add 'Room Charge' to Mode of Payment if not exists
    if not frappe.db.exists("Mode of Payment", "Room Charge"):
        mode = frappe.new_doc("Mode of Payment")
        mode.mode_of_payment = "Room Charge"
        mode.type = "General"
        mode.insert()

    # Add 'hotel_room' field to POS Invoice if not exists
    if not frappe.db.exists("Custom Field", {"dt": "POS Invoice", "fieldname": "hotel_room"}):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "POS Invoice",
            "fieldname": "hotel_room",
            "label": "Hotel Room Number",
            "fieldtype": "Link",
            "options": "Hotel Room",
            "insert_after": "customer"
        }).insert()

def create_default_data():
    # Create default Allowance Reason Codes
    reasons = [
        {"code": "POST-ERR", "desc": "Posting Error", "mgr": 0},
        {"code": "GUEST-SAT", "desc": "Guest Satisfaction / Complaint", "mgr": 1},
        {"code": "MGMT-COMP", "desc": "Management Complementary", "mgr": 1}
    ]
    
    for r in reasons:
        if not frappe.db.exists("Allowance Reason Code", r["code"]):
            frappe.get_doc({
                "doctype": "Allowance Reason Code",
                "reason_code": r["code"],
                "description": r["desc"],
                "requires_manager_approval": r["mgr"]
            }).insert()

    # Create Service Items
    items = [
        {"code": "ROOM-RENT", "name": "Room Rent"},
        {"code": "POS-CHARGE", "name": "POS Charge"},
        {"code": "PAYMENT", "name": "Payment Credit"}
    ]
    # Determine default Item Group
    target_item_group = "Services"
    if not frappe.db.exists("Item Group", "Services"):
        # Find the root item group
        root_item_group = frappe.db.get_value("Item Group", 
            {"parent_item_group": ["in", ["", None]], "is_group": 1}, "name")
        
        if not root_item_group:
             # Fallback: get any group
             root_item_group = frappe.db.get_value("Item Group", {"is_group": 1}, "name")
        
        if root_item_group:
            try:
                frappe.get_doc({
                    "doctype": "Item Group",
                    "item_group_name": "Services",
                    "parent_item_group": root_item_group,
                    "is_group": 0
                }).insert(ignore_permissions=True)
            except Exception:
                # If creation fails, fallback to using the root directly
                target_item_group = root_item_group
        else:
            # Last resort: grab any item group
            target_item_group = frappe.db.get_value("Item Group", {}, "name")
            
    for i in items:
        if not frappe.db.exists("Item", i["code"]):
            item = frappe.new_doc("Item")
            item.item_code = i["code"]
            item.item_name = i["name"]
            item.item_group = target_item_group
            item.is_stock_item = 0
            item.insert(ignore_permissions=True)