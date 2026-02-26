import frappe
from frappe import _
from frappe.utils import flt
from hospitality_core.hospitality_core.api.folio import mirror_to_company_folio

def process_room_charge(doc, method=None):
    """
    Hook: POS Invoice (on_submit)
    Logic: Breaks down the POS Invoice and posts EACH item to the Guest Folio.
    """
    
    # 1. Calculate how much of this invoice is being charged to the room
    room_charge_payment = 0
    for pay in doc.payments:
        if pay.mode_of_payment == "Room Charge":
            room_charge_payment += flt(pay.amount)
            
    if room_charge_payment <= 0:
        return

    # 2. Get the Room and Active Folio
    if not doc.get("hotel_room"):
        # FALLBACK: Try to find an active folio for this customer
        customer = doc.get("customer")
        if customer:
            # 1. Try finding via direct company link on Folio
            folios = frappe.get_all("Guest Folio", filters={
                "status": "Open",
                "company": customer
            }, fields=["room", "name"])
            
            # 2. Try finding via Guest link if no direct company folio
            if not folios:
                guests = frappe.get_all("Guest", filters={"customer": customer}, fields=["name"])
                if guests:
                    folios = frappe.get_all("Guest Folio", filters={
                        "status": "Open",
                        "guest": ["in", [g.name for g in guests]]
                    }, fields=["room", "name"])
            
            if len(folios) == 1:
                doc.hotel_room = folios[0].room
                # Update the document to persist the room back to DB
                frappe.db.set_value(doc.doctype, doc.name, "hotel_room", doc.hotel_room)
                frappe.msgprint(_("Auto-linked Room {0} from active Folio {1}").format(doc.hotel_room, folios[0].name))
            elif len(folios) > 1:
                 frappe.throw(_("Multiple active folios found for this customer ({0}). Please select a Room Number manually.").format(customer))
                 
    if not doc.get("hotel_room"):
        frappe.throw(_("Please select a Hotel Room for the Room Charge."))

    folio_name = frappe.db.get_value("Guest Folio", 
        {"room": doc.hotel_room, "status": "Open"}, "name"
    )
    
    if not folio_name:
        frappe.throw(_("No open Folio found for Room {0}.").format(doc.hotel_room))

    # 3. Determine the ratio (in case of split payments like half cash / half room charge)
    # This ensures the sales price on the folio matches the portion charged to the room
    invoice_total = flt(doc.grand_total)
    ratio = room_charge_payment / invoice_total if invoice_total > 0 else 1

    # 4. Determine Bill To logic (Company vs Guest)
    bill_to = "Guest"
    res_name = frappe.db.get_value("Guest Folio", folio_name, "reservation")
    if res_name:
        # Check if POS Posting is allowed for this reservation
        res_details = frappe.db.get_value("Hotel Reservation", res_name, ["is_company_guest", "allow_pos_posting"], as_dict=True)
        
        if not res_details.allow_pos_posting:
            frappe.throw(_("Room {0} is closed for POS Posting.").format(doc.hotel_room))

        if res_details.is_company_guest:
            bill_to = "Company"

    # 5. POST EACH ITEM INDIVIDUALLY
    for item in doc.items:
        # Calculate the actual price for this item based on the room charge portion
        posted_amount = flt(item.amount) * ratio
        
        txn = frappe.get_doc({
            "doctype": "Folio Transaction",
            "parent": folio_name,
            "parenttype": "Guest Folio",
            "parentfield": "transactions",
            "posting_date": doc.posting_date,
            "item": item.item_code, # Uses the actual item bought (e.g., 'HEINEKEN')
            "description": f"{item.item_name} (POS: {doc.name})",
            "qty": item.qty,
            "amount": posted_amount, # This is the sales price from the POS
            "bill_to": bill_to,
            "reference_doctype": "POS Invoice",
            "reference_name": doc.name,
            "is_invoiced": 1
        })
        txn.insert(ignore_permissions=True)

        # Mirror to Company Folio if the guest is a corporate guest
        if bill_to == "Company":
            mirror_to_company_folio(txn)

    # 6. Refresh the Folio Balance
    from hospitality_core.hospitality_core.api.folio import sync_folio_balance
    sync_folio_balance(frappe.get_doc("Guest Folio", folio_name))

    frappe.msgprint(_("Posted {0} items from POS to Folio {1}").format(len(doc.items), folio_name))

def void_room_charge(doc, method=None):
    """
    Hook: POS Invoice (on_cancel)
    Logic: Deletes all folio transactions linked to this POS Invoice.
    Requirement: "the transaction should be located and the row deleted"
    """
    # 1. Find all Folio Transactions linked to this POS Invoice
    transactions = frappe.get_all("Folio Transaction", 
        filters={"reference_doctype": "POS Invoice", "reference_name": doc.name},
        fields=["name", "parent"]
    )

    if not transactions:
        return

    affected_folios = set()
    for txn in transactions:
        affected_folios.add(txn.parent)
        
        # 2. Find mirror transactions
        mirror_txns = frappe.get_all("Folio Transaction",
            filters={"reference_doctype": "Folio Transaction", "reference_name": txn.name},
            fields=["name", "parent"]
        )
        for m_txn in mirror_txns:
            affected_folios.add(m_txn.parent)
            frappe.delete_doc("Folio Transaction", m_txn.name, ignore_permissions=True)

        # Delete the original transaction
        frappe.delete_doc("Folio Transaction", txn.name, ignore_permissions=True)

    # 3. Sync all affected folios
    from hospitality_core.hospitality_core.api.folio import sync_folio_balance
    for folio_name in affected_folios:
        if frappe.db.exists("Guest Folio", folio_name):
            sync_folio_balance(frappe.get_doc("Guest Folio", folio_name))

    frappe.msgprint(_("Removed {0} items from Folio(s) due to POS Invoice cancellation.").format(len(transactions)))

@frappe.whitelist()
def get_guest_details_from_room(room_number):
    """
    Fetches the Customer linked to the currently active (Open) Guest Folio for a given room.
    """
    if not room_number:
        return {}

    # Find the Open Folio for this room
    folio = frappe.db.get_value("Guest Folio", 
        {"room": room_number, "status": "Open"}, 
        ["name", "reservation"], 
        as_dict=True
    )

    if not folio:
        return {"error": _("No active check-in found for Room {0}").format(room_number)}

    # Get the Customer from the Reservation
    if not folio.reservation:
        return {"error": _("No reservation linked to the active folio.")}

    # Fetch Guest and Company details from Reservation
    res_details = frappe.db.get_value("Hotel Reservation", folio.reservation, 
        ["guest", "is_company_guest", "company"], as_dict=True)
    
    if not res_details:
        return {"error": _("Reservation not found.")}

    customer = None
    customer_name = ""

    if res_details.is_company_guest and res_details.company:
        customer = res_details.company
    elif res_details.guest:
        # Fetch customer linked to the Guest
        customer = frappe.db.get_value("Guest", res_details.guest, "customer")
    
    if not customer:
        return {"error": _("No ERPNext Customer linked to the Guest/Reservation.")}
        
    customer_name = frappe.db.get_value("Customer", customer, "customer_name")

    return {
        "customer": customer,
        "customer_name": customer_name,
        "folio": folio.name
    }