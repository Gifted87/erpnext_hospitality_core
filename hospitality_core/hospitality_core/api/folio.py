import frappe
from frappe import _
from frappe.utils import flt

def sync_folio_balance(doc, method=None):
    """
    Recalculates Total Charges, Total Payments, and Outstanding Balance.
    Triggered on: Guest Folio (on_update), Folio Transaction (after_save/on_trash).
    """
    # If called from Child Table event, doc is the child
    if doc.doctype == "Folio Transaction":
        folio_name = doc.parent
        # Trigger Mirroring only on new/updated transactions
        # We skip mirroring for transfer items to avoid zeroing out the Master Folio at checkout
        if not doc.is_void and doc.item not in ["TRANSFER", "TRANSFER-GROUP"]:
            if doc.bill_to == "Company":
                mirror_to_company_folio(doc)
            elif doc.bill_to == "Group":
                mirror_to_group_folio(doc)
    else:
        folio_name = doc.name

    # Aggregation Query
    # We filter out void transactions
    # Separate Actual Payments from Discounts/Complimentary items
    totals = frappe.db.sql("""
        SELECT 
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as charges,
            SUM(CASE 
                WHEN amount < 0 AND item NOT IN ('DISCOUNT', 'COMPLIMENTARY') THEN ABS(amount) 
                ELSE 0 END) as payments,
            SUM(CASE 
                WHEN amount < 0 AND item IN ('DISCOUNT', 'COMPLIMENTARY') THEN ABS(amount) 
                ELSE 0 END) as discounts
        FROM `tabFolio Transaction`
        WHERE parent = %s AND is_void = 0
    """, (folio_name,), as_dict=True)[0]

    total_charges = totals.charges or 0.0
    total_payments = totals.payments or 0.0
    total_discounts = totals.discounts or 0.0
    outstanding = total_charges - total_payments - total_discounts
    excess_payment = abs(outstanding) if outstanding < -0.01 else 0.0

    # Direct DB update
    frappe.db.set_value("Guest Folio", folio_name, {
        "total_charges": total_charges,
        "total_payments": total_payments,
        "total_discounts": total_discounts,
        "outstanding_balance": outstanding,
        "excess_payment": excess_payment
    })
    
    # Check Credit Limit if linked to Company
    folio_company = frappe.db.get_value("Guest Folio", folio_name, "company")
    if folio_company and outstanding > 0:
        check_credit_limit(folio_company, outstanding)

def check_credit_limit(customer_id, current_exposure):
    """
    Checks if the Customer has exceeded their Credit Limit including current exposure.
    """
    try:
        hotel_company = frappe.defaults.get_user_default("Company")
        if not hotel_company:
            hotel_company = frappe.db.get_single_value("Global Defaults", "default_company")
        
        if not hotel_company:
            return

        credit_limit = 0.0
        
        # 1. Try Child Table (v15+)
        if frappe.db.get_value("DocType", "Customer Credit Limit", "name"):
            credit_limit = frappe.db.get_value("Customer Credit Limit", 
                {"parent": customer_id, "company": hotel_company}, 
                "credit_limit"
            )
        
        # 2. Fallback to main field
        if not credit_limit:
             credit_limit = frappe.db.get_value("Customer", customer_id, "credit_limit")

        if not credit_limit or flt(credit_limit) <= 0:
            return

        # Get current ERP Balance for Customer
        erp_balance = 0.0
        try:
            from erpnext.accounts.utils import get_balance_on
            erp_balance = get_balance_on(party_type="Customer", party=customer_id)
        except ImportError:
            erp_balance = frappe.db.get_value("Customer", customer_id, "total_unpaid") or 0.0
        except Exception:
            pass

        total_liability = flt(erp_balance) + flt(current_exposure)
        
        if total_liability > flt(credit_limit):
            frappe.msgprint(_("Warning: Credit Limit Exceeded for {0}. Limit: {1}, Liability: {2}").format(
                customer_id, 
                frappe.format(credit_limit, "Currency"), 
                frappe.format(total_liability, "Currency")
            ), alert=True)

    except Exception as e:
        frappe.log_error(f"Credit Limit Check Failed for {customer_id}: {str(e)}", "Hospitality Core")

def mirror_to_company_folio(transaction_doc):
    """
    If a transaction is Bill To Company, we post a copy to the Company's Master Folio.
    Updates: Ensures description contains Guest/Reservation info.
    """
    # 1. Identify the Company
    guest_folio = frappe.get_doc("Guest Folio", transaction_doc.parent)
    company = guest_folio.company
    
    if not company:
        return

    # 2. Find Master Folio for Company
    master_folio = frappe.db.get_value("Guest Folio", {
        "company": company, 
        "status": "Open",
        "is_company_master": 1,
        "name": ["!=", guest_folio.name]
    }, "name")

    # If no master exists, we skip. It usually should be created at Reservation Check-in.
    if not master_folio:
        return

    # 3. Check if already mirrored
    exists = frappe.db.exists("Folio Transaction", {
        "parent": master_folio,
        "reference_name": transaction_doc.name,
        "reference_doctype": "Folio Transaction"
    })
    
    if exists:
        return

    # 4. Create Mirror Transaction
    # Enhanced Description for clarity on Master Bill: "Original Desc [Res: ID (Guest Name)]"
    ref_info = ""
    if guest_folio.reservation:
        ref_info = f"Res: {guest_folio.reservation}"
        # Fetch guest name if not evident
        guest_name = frappe.db.get_value("Hotel Reservation", guest_folio.reservation, "guest")
        if guest_name:
            guest_full_name = frappe.db.get_value("Guest", guest_name, "full_name")
            ref_info += f" ({guest_full_name})"
    else:
        ref_info = f"Room: {guest_folio.room}"
    
    new_txn = frappe.get_doc({
        "doctype": "Folio Transaction",
        "parent": master_folio,
        "parenttype": "Guest Folio",
        "parentfield": "transactions",
        "posting_date": transaction_doc.posting_date,
        "item": transaction_doc.item,
        "description": f"{transaction_doc.description} [{ref_info}]",
        "qty": transaction_doc.qty,
        "amount": transaction_doc.amount,
        "bill_to": "Company",
        "reference_doctype": "Folio Transaction",
        "reference_name": transaction_doc.name,
        "is_void": 0
    })
    new_txn.insert(ignore_permissions=True)
    
    # Sync Company Folio Balance
    sync_folio_balance(frappe.get_doc("Guest Folio", master_folio))

def mirror_to_group_folio(transaction_doc):
    """
    If a transaction is Bill To Group, we post a copy to the Group's Master Folio.
    """
    # 1. Identify the Group
    guest_folio = frappe.get_doc("Guest Folio", transaction_doc.parent)
    reservation = guest_folio.reservation
    
    if not reservation:
        return

    group_booking = frappe.db.get_value("Hotel Reservation", reservation, "group_booking")
    if not group_booking:
        return

    # 2. Find Master Folio for Group
    master_folio = frappe.db.get_value("Hotel Group Booking", group_booking, "master_folio")

    # If no master exists, we skip.
    if not master_folio or master_folio == guest_folio.name:
        return

    # 3. Check if already mirrored
    exists = frappe.db.exists("Folio Transaction", {
        "parent": master_folio,
        "reference_name": transaction_doc.name,
        "reference_doctype": "Folio Transaction"
    })
    
    if exists:
        return

    # 4. Create Mirror Transaction
    guest_name = frappe.db.get_value("Hotel Reservation", reservation, "guest")
    guest_full_name = frappe.db.get_value("Guest", guest_name, "full_name") if guest_name else "Unknown"
    
    ref_info = f"Res: {reservation} ({guest_full_name}) | Room: {guest_folio.room}"
    
    new_txn = frappe.get_doc({
        "doctype": "Folio Transaction",
        "parent": master_folio,
        "parenttype": "Guest Folio",
        "parentfield": "transactions",
        "posting_date": transaction_doc.posting_date,
        "item": transaction_doc.item,
        "description": f"{transaction_doc.description} [{ref_info}]",
        "qty": transaction_doc.qty,
        "amount": transaction_doc.amount,
        "bill_to": "Group",
        "reference_doctype": "Folio Transaction",
        "reference_name": transaction_doc.name,
        "is_void": 0
    })
    new_txn.insert(ignore_permissions=True)
    
    # Sync Group Folio Balance
    sync_folio_balance(frappe.get_doc("Guest Folio", master_folio))

@frappe.whitelist()
def move_transactions(transaction_names, target_folio):
    """
    Moves selected transactions from Source Folio to Target Folio.
    """
    if not ("Frontdesk Supervisor" in frappe.get_roles() or frappe.session.user == "Administrator"):
        frappe.throw(_("Access Denied. Only Frontdesk Supervisors can move transactions."))

    if isinstance(transaction_names, str):
        import json
        transaction_names = json.loads(transaction_names)

    if not transaction_names:
        frappe.throw(_("No transactions selected"))

    target_doc = frappe.get_doc("Guest Folio", target_folio)
    if target_doc.status != "Open":
        frappe.throw(_("Target Folio must be Open"))

    source_folio_name = None

    for txn_name in transaction_names:
        txn = frappe.get_doc("Folio Transaction", txn_name)
        
        if txn.is_invoiced:
            frappe.throw(_("Cannot move invoiced transaction: {0}").format(txn.description))
            
        source_folio_name = txn.parent
        
        # Log the move before updating parent
        log = frappe.get_doc({
            "doctype": "Folio Transaction Move Log",
            "transaction_name": txn.name,
            "source_folio": source_folio_name,
            "target_folio": target_folio,
            "item": txn.item,
            "amount": txn.amount,
            "user": frappe.session.user,
            "move_datetime": frappe.utils.now_datetime()
        })
        log.insert(ignore_permissions=True)

        # Move: Update Parent
        frappe.db.set_value("Folio Transaction", txn.name, "parent", target_folio)
        
        # Audit Trail
        txn.add_comment("Info", _("Moved from Folio {0} to {1}").format(source_folio_name, target_folio))

    # Sync Balances for both
    if source_folio_name:
        sync_folio_balance(frappe.get_doc("Guest Folio", source_folio_name))
    
    sync_folio_balance(target_doc)
    
    return True
@frappe.whitelist()
def debug_folio_totals(folio_name):
    """
    Diagnostic tool to see raw SQL vs field values.
    """
    totals = frappe.db.sql("""
        SELECT 
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as charges,
            SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as payments
        FROM `tabFolio Transaction`
        WHERE parent = %s AND is_void = 0
    """, (folio_name,), as_dict=True)[0]
    
    doc = frappe.get_doc("Guest Folio", folio_name)
    
    txns = frappe.db.get_all("Folio Transaction", 
        filters={"parent": folio_name, "is_void": 0},
        fields=["name", "item", "description", "amount"]
    )
    
    return {
        "sql_totals": totals,
        "doc_fields": {
            "total_charges": doc.total_charges,
            "total_payments": doc.total_payments,
            "total_discounts": doc.total_discounts,
            "outstanding_balance": doc.outstanding_balance
        },
        "transactions": txns
    }

def record_guest_balance(folio_doc):
    """
    If a folio is closed with a credit balance (outstanding_balance < 0),
    record it in the Guest Balance Ledger.
    """
    if flt(folio_doc.outstanding_balance) < -0.01:
        credit_amount = abs(flt(folio_doc.outstanding_balance))
        
        # Check if already recorded to avoid duplicates
        if not frappe.db.exists("Guest Balance Ledger", {"folio": folio_doc.name}):
            ledger_entry = frappe.new_doc("Guest Balance Ledger")
            ledger_entry.guest = folio_doc.guest
            ledger_entry.folio = folio_doc.name
            ledger_entry.amount = credit_amount
            ledger_entry.status = "Available"
            ledger_entry.insert(ignore_permissions=True)
            
            frappe.msgprint(_("Recorded credit balance of {0} for Guest {1} in Balance Ledger.").format(
                frappe.format(credit_amount, "Currency"), folio_doc.guest
            ))

def transfer_existing_balances(folio_doc):
    """
    Checks for available credit balances for the guest and transfers them to the new folio.
    """
    if not folio_doc.guest:
        return

    available_balances = frappe.get_all("Guest Balance Ledger", 
        filters={"guest": folio_doc.guest, "status": "Available"},
        fields=["name", "amount", "folio"]
    )

    if not available_balances:
        return

    total_transferred = 0.0
    for balance in available_balances:
        # Create a payment transaction in the new folio
        txn = frappe.get_doc({
            "doctype": "Folio Transaction",
            "parent": folio_doc.name,
            "parenttype": "Guest Folio",
            "parentfield": "transactions",
            "posting_date": frappe.utils.nowdate(),
            "item": "BALANCE-TRANSFER",
            "description": f"Balance Transfer from Folio {balance.folio}",
            "qty": 1,
            "amount": -1 * flt(balance.amount), # Payment (Credit)
            "is_void": 0
        })
        
        # Ensure BALANCE-TRANSFER item exists
        if not frappe.db.exists("Item", "BALANCE-TRANSFER"):
            item = frappe.new_doc("Item")
            item.item_code = "BALANCE-TRANSFER"
            item.item_name = "Guest Balance Transfer"
            item.item_group = "Services"
            item.is_stock_item = 0
            item.insert(ignore_permissions=True)
            
        txn.insert(ignore_permissions=True)
        
        # Update Ledger Status
        frappe.db.set_value("Guest Balance Ledger", balance.name, {
            "status": "Transferred",
            "transferred_to_folio": folio_doc.name
        })
        
        total_transferred += flt(balance.amount)

    if total_transferred > 0:
        sync_folio_balance(folio_doc)
        frappe.msgprint(_("Transferred {0} from previous credit balances to this folio.").format(
            frappe.format(total_transferred, "Currency")
        ))
