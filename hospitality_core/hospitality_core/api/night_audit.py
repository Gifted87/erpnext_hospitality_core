import frappe
from frappe import _
from frappe.utils import add_days, nowdate, getdate, flt
from hospitality_core.hospitality_core.api.folio import sync_folio_balance, mirror_to_company_folio, mirror_to_group_folio

def run_daily_audit():
    """
    Scheduled Job: Runs at 2 PM daily.
    1. Checks for Overstays.
    2. Posts Room Rent + Discounts for all rooms currently Checked In.
    3. SKIPS posting if a Room Rent charge already exists for the current date.
    """
    posting_date = nowdate()
    
    # 1. Fetch active reservations with Discount settings
    active_reservations = frappe.get_all("Hotel Reservation", 
        filters={"status": "Checked In"},
        fields=[
            "name", "guest", "room", "room_type", "rate_plan", 
            "departure_date", "company", "folio",
            "is_complimentary", "discount_type", "discount_value",
            "is_company_guest", "is_group_guest", "group_booking"
        ]
    )

    count = 0
    for res in active_reservations:
        try:
            if process_single_reservation(res, posting_date):
                count += 1
        except Exception as e:
            # Truncate title to 140 characters to prevent CharacterLengthExceededError
            error_title = f"Night Audit Error: {res.name}"
            error_message = f"Night Audit Failure for Reservation {res.name}: {str(e)}"
            frappe.log_error(error_message, error_title)

    if count > 0:
        frappe.msgprint(_("Auto-Bill (2 PM): Posted charges for {0} rooms.").format(count))

def process_single_reservation(res, posting_date):
    # First, check if already charged to avoid duplicates
    if already_charged_today(res.folio, posting_date, room=res.room):
        return False
    
    # Handle true overstays (departure was BEFORE today, not today)
    # Guests departing today should still be charged for their final night
    if getdate(res.departure_date) < getdate(posting_date):
        handle_overstay(res)

    # Get Base Rate
    daily_rate = get_rate(res.rate_plan, res.room_type, posting_date)
    
    if daily_rate > 0:
        post_room_charge(res, daily_rate, posting_date)
        return True
        
    return False

def already_charged_today(folio_name, date, room=None):
    filters = {
        "parent": folio_name,
        "posting_date": date,
        "is_void": 0,
        "item": ["in", get_room_rent_item_codes()] 
    }
    if room:
        # Crucial for Group Payer Folio which contains mirrored charges for many rooms
        filters["description"] = ["like", f"%{room}%"]
        
    return frappe.db.exists("Folio Transaction", filters)

def get_room_rent_item_codes():
    return frappe.db.sql_list("SELECT name FROM `tabItem` WHERE item_code='ROOM-RENT' OR item_group='Accommodation'")

def handle_overstay(res):
    new_departure = add_days(nowdate(), 1)
    # Use db.set_value to skip validation when auto-extending overstays
    # This prevents conflicts with other reservations in the same room
    frappe.db.set_value("Hotel Reservation", res.name, "departure_date", new_departure)
    frappe.db.set_value("Hotel Reservation", res.name, "_user_tags", "Overstay")
    # Add system comment to track the extension
    doc = frappe.get_doc("Hotel Reservation", res.name)
    doc.add_comment("Info", _("Auto-Extended: Guest still in-house at 2 PM."))

def get_rate(rate_plan, room_type, date):
    if not rate_plan:
        return frappe.db.get_value("Hotel Room Type", room_type, "default_rate")
    
    plan = frappe.get_doc("Room Rate Plan", rate_plan)
    if getdate(date) >= getdate(plan.valid_from) and getdate(date) <= getdate(plan.valid_to):
        return plan.rate
    else:
        return frappe.db.get_value("Hotel Room Type", room_type, "default_rate")

def post_room_charge(res, base_amount, date):
    """
    Posts Rent AND Discount transaction if applicable.
    Called by Night Audit AND Check-In process.
    Updates: Checks res.is_company_guest to force 'Company' billing and mirroring.
    """
    folio_name = res.folio
    if not folio_name:
        return
        
    ensure_item_exists("ROOM-RENT", "Room Rent")

    # Determine Bill To
    bill_to = "Guest"
    
    # 1. PRIORITY: Check if flagged as Company Guest
    if res.is_company_guest:
        bill_to = "Company"
    # 2. PRIORITY: Check if flagged as Group Guest
    elif res.get("is_group_guest") and res.get("group_booking"):
        bill_to = "Group"
    else:
        # 3. FALLBACK: Check Routing Instructions
        rent_item_group = frappe.db.get_value("Item", "ROOM-RENT", "item_group")
        routings = frappe.get_all("Reservation Routing", filters={"parent": res.name}, fields=["item_group", "bill_to"])
        for rule in routings:
            if rule.item_group == rent_item_group:
                bill_to = rule.bill_to
                break

    # 1. Post Base Charge
    txn = frappe.get_doc({
        "doctype": "Folio Transaction",
        "parent": folio_name,
        "parenttype": "Guest Folio",
        "parentfield": "transactions",
        "posting_date": date,
        "item": "ROOM-RENT", 
        "description": f"Room Charge - {res.room}",
        "qty": 1,
        "amount": base_amount,
        "bill_to": bill_to
    }).insert(ignore_permissions=True)

    # EXPLICIT MIRRORING
    if bill_to == "Company":
        mirror_to_company_folio(txn)
    elif bill_to == "Group":
        mirror_to_group_folio(txn)

    # 2. Calculate and Post Discount
    discount_amount = 0.0
    discount_desc = ""
    discount_item = "DISCOUNT"

    # DEBUG: Log discount info
    frappe.log_error(f"Posting Charge for {res.name}: type={res.get('discount_type')}, value={res.get('discount_value')}, comp={res.get('is_complimentary')}", "Post Charge Discount Debug")

    if res.get("is_complimentary"):
        discount_amount = base_amount
        discount_desc = "Complimentary Adjustment"
        discount_item = "COMPLIMENTARY"
    elif str(res.discount_type).strip() == "Percentage":
        pct = flt(res.discount_value)
        discount_amount = base_amount * (pct / 100.0)
        discount_desc = f"Room Discount ({pct}%)"
    elif str(res.discount_type).strip() == "Amount":
        discount_amount = flt(res.discount_value)
        discount_desc = "Room Discount (Fixed)"

    if discount_amount > 0:
        ensure_item_exists(discount_item, discount_desc)
        
        disc_txn = frappe.get_doc({
            "doctype": "Folio Transaction",
            "parent": folio_name,
            "parenttype": "Guest Folio",
            "parentfield": "transactions",
            "posting_date": date,
            "item": discount_item, 
            "description": discount_desc,
            "qty": 1,
            "amount": -1 * discount_amount, # Negative for credit/reduction
            "bill_to": bill_to
        }).insert(ignore_permissions=True)

        # EXPLICIT MIRRORING: Mirror discount if applicable
        if bill_to == "Company":
            mirror_to_company_folio(disc_txn)
        elif bill_to == "Group":
            mirror_to_group_folio(disc_txn)

    # Sync Balance
    sync_folio_balance(frappe.get_doc("Guest Folio", folio_name))

def ensure_item_exists(code, name):
    if not frappe.db.exists("Item", code):
        item = frappe.new_doc("Item")
        item.item_code = code
        item.item_name = name
        item.item_group = "Services"
        item.is_stock_item = 0
        item.insert(ignore_permissions=True)