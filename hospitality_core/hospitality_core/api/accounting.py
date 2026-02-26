import frappe
from frappe import _
from frappe.utils import flt

def get_tax_breakdown(total_amount):
    """
    Returns a breakdown of an inclusive amount:
    Total = Net + 5% CT + 7.5% VAT + 10% SC = 1.225 * Net
    """
    total_amount = flt(total_amount)
    net_amount = flt(total_amount / 1.225, 2)
    ct_amount = flt(net_amount * 0.05, 2)
    vat_amount = flt(net_amount * 0.075, 2)
    sc_amount = flt(net_amount * 0.10, 2)
    
    # Adjust net for rounding differences to ensure total matches
    total_deduction = ct_amount + vat_amount + sc_amount
    net_amount = flt(total_amount - total_deduction, 2)
    
    return {
        "net_amount": net_amount,
        "ct_amount": ct_amount,
        "vat_amount": vat_amount,
        "sc_amount": sc_amount,
        "total_deduction": total_deduction,
        "total_amount": total_amount
    }

def make_gl_entries_for_folio_transaction(txn_doc, method=None):
    """
    Creates GL entries for a Folio Transaction (Charge).
    dr Receivable / cr Suspense
    """
    if flt(txn_doc.amount) <= 0 or txn_doc.item in ["PAYMENT", "DISCOUNT", "COMPLIMENTARY"]:
        return

    # Handle Cancellation/Void
    is_cancelled = False
    if method == "on_cancel" or txn_doc.docstatus == 2 or getattr(txn_doc, "is_void", 0):
        is_cancelled = True

    # Skip if originated from POS Invoice (POS Invoice creates its own GL entries)
    if txn_doc.reference_doctype == "POS Invoice":
        return

    settings = frappe.get_single("Hospitality Accounting Settings")
    
    # 1. Identify Customer (Party)
    guest_folio = frappe.get_doc("Guest Folio", txn_doc.parent)
    customer = guest_folio.company
    
    if not customer:
        customer = frappe.db.get_value("Guest", guest_folio.guest, "customer")
    
    if not customer:
        return

    # 2. Check if already created (matching this specific flow: original or reversal)
    check_debit = flt(txn_doc.amount) if not is_cancelled else 0
    if frappe.db.exists("GL Entry", {
        "remarks": ["like", f"%Ref: {txn_doc.name}%"],
        "debit": check_debit,
        "account": settings.receivable_account,
        "is_cancelled": 1 if is_cancelled else 0
    }):
        return

    gl_entries = []
    
    # Debit Receivable
    gl_entries.append(frappe.get_doc({
        "doctype": "GL Entry",
        "posting_date": txn_doc.posting_date,
        "account": settings.receivable_account,
        "party_type": "Customer",
        "party": customer,
        "debit": flt(txn_doc.amount) if not is_cancelled else 0,
        "credit": 0 if not is_cancelled else flt(txn_doc.amount),
        "voucher_type": "Guest Folio",
        "voucher_no": txn_doc.parent,
        "remarks": f"{txn_doc.description} (Ref: {txn_doc.name})",
        "is_cancelled": 1 if is_cancelled else 0,
        "cost_center": settings.cost_center,
        "company": "Edo Heritage Hotel"
    }))

    # Credits
    total_amount = flt(txn_doc.amount)
    
    # Calculate Inclusive Splits
    # Total = Net + 0.05*Net + 0.075*Net + 0.10*Net = 1.225 * Net
    net_amount = flt(total_amount / 1.225, 2)
    ct_amount = flt(net_amount * 0.05, 2)
    vat_amount = flt(net_amount * 0.075, 2)
    sc_amount = flt(net_amount * 0.10, 2)

    # 1. Credit Suspense (Net Revenue)
    gl_entries.append(frappe.get_doc({
        "doctype": "GL Entry",
        "posting_date": txn_doc.posting_date,
        "account": settings.income_suspense_account,
        "debit": 0 if not is_cancelled else net_amount,
        "credit": net_amount if not is_cancelled else 0,
        "voucher_type": "Guest Folio",
        "voucher_no": txn_doc.parent,
        "remarks": f"{txn_doc.description} (Net) (Ref: {txn_doc.name})",
        "is_cancelled": 1 if is_cancelled else 0,
        "cost_center": settings.cost_center,
        "company": "Edo Heritage Hotel"
    }))

    # 2. Credit Consumption Tax
    if ct_amount > 0:
        gl_entries.append(frappe.get_doc({
            "doctype": "GL Entry",
            "posting_date": txn_doc.posting_date,
            "account": settings.consumption_tax_account,
            "debit": 0 if not is_cancelled else ct_amount,
            "credit": ct_amount if not is_cancelled else 0,
            "voucher_type": "Guest Folio",
            "voucher_no": txn_doc.parent,
            "remarks": f"Consumption Tax (5%) for {txn_doc.name}",
            "is_cancelled": 1 if is_cancelled else 0,
            "cost_center": settings.cost_center,
            "company": "Edo Heritage Hotel"
        }))

    # 3. Credit VAT
    if vat_amount > 0:
        gl_entries.append(frappe.get_doc({
            "doctype": "GL Entry",
            "posting_date": txn_doc.posting_date,
            "account": settings.vat_account,
            "debit": 0 if not is_cancelled else vat_amount,
            "credit": vat_amount if not is_cancelled else 0,
            "voucher_type": "Guest Folio",
            "voucher_no": txn_doc.parent,
            "remarks": f"VAT (7.5%) for {txn_doc.name}",
            "is_cancelled": 1 if is_cancelled else 0,
            "cost_center": settings.cost_center,
            "company": "Edo Heritage Hotel"
        }))

    # 4. Credit Service Charge
    if sc_amount > 0:
        gl_entries.append(frappe.get_doc({
            "doctype": "GL Entry",
            "posting_date": txn_doc.posting_date,
            "account": settings.service_charge_account,
            "debit": 0 if not is_cancelled else sc_amount,
            "credit": sc_amount if not is_cancelled else 0,
            "voucher_type": "Guest Folio",
            "voucher_no": txn_doc.parent,
            "remarks": f"Service Charge (10%) for {txn_doc.name}",
            "is_cancelled": 1 if is_cancelled else 0,
            "cost_center": settings.cost_center,
            "company": "Edo Heritage Hotel"
        }))

    for entry in gl_entries:
        entry.insert(ignore_permissions=True)

def handle_payment_income_realization(payment_doc, folio_id, amount, cancel=0):
    """
    Transfers amount from Suspense to Income upon Payment.
    dr Suspense / cr Income
    Only the Net portion is transferred, as Taxes were already split into 
    total liability accounts during the Folio Transaction (Charge).
    """
    settings = frappe.get_single("Hospitality Accounting Settings")
    
    # Calculate Net portion: Total = 1.225 * Net
    net_amount = flt(abs(flt(amount)) / 1.225, 2)
    
    gl_entries = []

    # Debit Suspense
    gl_entries.append(frappe.get_doc({
        "doctype": "GL Entry",
        "posting_date": payment_doc.posting_date,
        "account": settings.income_suspense_account,
        "debit": net_amount if not cancel else 0,
        "credit": 0 if not cancel else net_amount,
        "voucher_type": "Payment Entry",
        "voucher_no": payment_doc.name,
        "remarks": f"Income Realization (Net) for Folio {folio_id}",
        "cost_center": settings.cost_center,
        "company": "Edo Heritage Hotel"
    }))

    # Credit Income
    gl_entries.append(frappe.get_doc({
        "doctype": "GL Entry",
        "posting_date": payment_doc.posting_date,
        "account": settings.income_account,
        "debit": 0 if not cancel else net_amount,
        "credit": net_amount if not cancel else 0,
        "voucher_type": "Payment Entry",
        "voucher_no": payment_doc.name,
        "remarks": f"Income Realization (Net) for Folio {folio_id}",
        "cost_center": settings.cost_center,
        "company": "Edo Heritage Hotel"
    }))

    for entry in gl_entries:
        entry.insert(ignore_permissions=True)

def redirect_pos_income_to_suspense(pos_invoice, method=None):
    """
    Hook: POS Invoice (on_submit/on_cancel)
    Redirects the portion charged to room from Income to Suspense.
    dr Income / cr Suspense
    """
    is_cancelled = False
    if method == "on_cancel" or pos_invoice.docstatus == 2:
        is_cancelled = True

    room_charge_amount = 0
    for pay in pos_invoice.payments:
        if pay.mode_of_payment == "Room Charge":
            room_charge_amount += flt(pay.amount)

    if room_charge_amount <= 0:
        return

    settings = frappe.get_single("Hospitality Accounting Settings")
    
    from erpnext.accounts.general_ledger import make_gl_entries
    
    gl_entries = []

    # 1. Debit Income (Reduce Realized Income)
    gl_entries.append(frappe._dict({
        "account": settings.income_account,
        "debit": abs(flt(room_charge_amount)),
        "credit": 0,
        "posting_date": pos_invoice.posting_date,
        "voucher_type": "POS Invoice",
        "voucher_no": pos_invoice.name,
        "remarks": f"Deferring Income for Room Charge (Invoice {pos_invoice.name})",
        "cost_center": settings.cost_center,
        "company": "Edo Heritage Hotel"
    }))

    # 2. Credit Suspense (Increase Unearned)
    gl_entries.append(frappe._dict({
        "account": settings.income_suspense_account,
        "debit": 0,
        "credit": abs(flt(room_charge_amount)),
        "posting_date": pos_invoice.posting_date,
        "voucher_type": "POS Invoice",
        "voucher_no": pos_invoice.name,
        "remarks": f"Deferring Income for Room Charge (Invoice {pos_invoice.name})",
        "cost_center": settings.cost_center,
        "company": "Edo Heritage Hotel"
    }))

    if gl_entries:
        make_gl_entries(gl_entries, cancel=is_cancelled, adv_adj=True)

def reclassify_pos_taxes(pos_invoice, method=None):
    """
    Hook: POS Invoice (on_submit/on_cancel)
    Deducts taxes from the full income realized by ERPNext POS and reclassifies them.
    Total = 1.225 * Net
    dr Income (or Suspense if Room Charge) / cr CT, VAT, SC
    """
    is_cancelled = False
    if method == "on_cancel" or pos_invoice.docstatus == 2:
        is_cancelled = True

    if pos_invoice.grand_total <= 0:
        return

    settings = frappe.get_single("Hospitality Accounting Settings")
    from erpnext.accounts.general_ledger import make_gl_entries

    total_amount = flt(pos_invoice.grand_total, 2)
    net_amount = flt(total_amount / 1.225, 2)
    
    # Calculate Tax Components (Rounded)
    ct_amount = flt(net_amount * 0.05, 2)
    vat_amount = flt(net_amount * 0.075, 2)
    sc_amount = flt(net_amount * 0.10, 2)
    
    total_tax = ct_amount + vat_amount + sc_amount
    
    # Determine Source of Funds (Income vs Suspense)
    room_charge_paid = 0
    for pay in pos_invoice.payments:
        if pay.mode_of_payment == "Room Charge":
            room_charge_paid += flt(pay.amount, 2)
            
    if room_charge_paid > total_amount:
        room_charge_paid = total_amount

    suspense_ratio = room_charge_paid / total_amount if total_amount > 0 else 0
    
    tax_from_suspense = flt(total_tax * suspense_ratio, 2)
    tax_from_income = flt(total_tax - tax_from_suspense, 2)

    gl_entries = []

    # 1. Debit Income (Tax portion of Cash/Card sales)
    if tax_from_income > 0:
        gl_entries.append(frappe._dict({
            "account": settings.income_account,
            "debit": tax_from_income,
            "credit": 0,
            "posting_date": pos_invoice.posting_date,
            "voucher_type": "POS Invoice",
            "voucher_no": pos_invoice.name,
            "remarks": f"Tax Reclassification (Income) for POS {pos_invoice.name}",
            "cost_center": settings.cost_center,
            "company": "Edo Heritage Hotel"
        }))

    # 2. Debit Suspense (Tax portion of Room Charges)
    if tax_from_suspense > 0:
        gl_entries.append(frappe._dict({
            "account": settings.income_suspense_account,
            "debit": tax_from_suspense,
            "credit": 0,
            "posting_date": pos_invoice.posting_date,
            "voucher_type": "POS Invoice",
            "voucher_no": pos_invoice.name,
            "remarks": f"Tax Reclassification (Suspense) for POS {pos_invoice.name}",
            "cost_center": settings.cost_center,
            "company": "Edo Heritage Hotel"
        }))

    # 3. Credit Consumption Tax
    if ct_amount > 0:
        gl_entries.append(frappe._dict({
            "account": settings.consumption_tax_account,
            "debit": 0,
            "credit": ct_amount,
            "posting_date": pos_invoice.posting_date,
            "voucher_type": "POS Invoice",
            "voucher_no": pos_invoice.name,
            "remarks": f"Consumption Tax (5%) for POS {pos_invoice.name}",
            "cost_center": settings.cost_center,
            "company": "Edo Heritage Hotel"
        }))

    # 4. Credit VAT
    if vat_amount > 0:
        gl_entries.append(frappe._dict({
            "account": settings.vat_account,
            "debit": 0,
            "credit": vat_amount,
            "posting_date": pos_invoice.posting_date,
            "voucher_type": "POS Invoice",
            "voucher_no": pos_invoice.name,
            "remarks": f"VAT (7.5%) for POS {pos_invoice.name}",
            "cost_center": settings.cost_center,
            "company": "Edo Heritage Hotel"
        }))

    # 5. Credit Service Charge
    if sc_amount > 0:
        gl_entries.append(frappe._dict({
            "account": settings.service_charge_account,
            "debit": 0,
            "credit": sc_amount,
            "posting_date": pos_invoice.posting_date,
            "voucher_type": "POS Invoice",
            "voucher_no": pos_invoice.name,
            "remarks": f"Service Charge (10%) for POS {pos_invoice.name}",
            "cost_center": settings.cost_center,
            "company": "Edo Heritage Hotel"
        }))

    if gl_entries:
        make_gl_entries(gl_entries, cancel=is_cancelled, adv_adj=True)

def create_expense_gl_entries(expense_doc, method=None):
    """
    Hook: Hospitality Expense (on_submit/on_cancel)
    """
    is_cancelled = False
    if method == "on_cancel" or expense_doc.docstatus == 2:
        is_cancelled = True

    if not expense_doc.expense_account or not expense_doc.payment_account:
        expense_doc.set_account_details()
        if not expense_doc.expense_account or not expense_doc.payment_account:
            frappe.throw(_("Expense Account and Payment Account are required for GL entries."))

    gl_entries = []
    company = expense_doc.company or "Edo Heritage Hotel"

    # 1. Debit Expense Account (Net Amount)
    gl_entries.append(frappe.get_doc({
        "doctype": "GL Entry",
        "posting_date": expense_doc.expense_date,
        "account": expense_doc.expense_account,
        "debit": abs(flt(expense_doc.amount)) if not is_cancelled else 0,
        "credit": 0 if not is_cancelled else abs(flt(expense_doc.amount)),
        "voucher_type": "Hospitality Expense",
        "voucher_no": expense_doc.name,
        "remarks": f"Expense: {expense_doc.expense_category} - {expense_doc.description or ''}",
        "is_cancelled": 1 if is_cancelled else 0,
        "cost_center": expense_doc.cost_center,
        "company": company
    }))

    # 2. Debit Tax Accounts (if any)
    for tax in expense_doc.get("taxes"):
        if flt(tax.tax_amount) > 0:
            gl_entries.append(frappe.get_doc({
                "doctype": "GL Entry",
                "posting_date": expense_doc.expense_date,
                "account": tax.account_head,
                "debit": abs(flt(tax.tax_amount)) if not is_cancelled else 0,
                "credit": 0 if not is_cancelled else abs(flt(tax.tax_amount)),
                "voucher_type": "Hospitality Expense",
                "voucher_no": expense_doc.name,
                "remarks": f"Tax: {tax.description or tax.account_head} for {expense_doc.name}",
                "is_cancelled": 1 if is_cancelled else 0,
                "cost_center": expense_doc.cost_center,
                "company": company
            }))

    # 3. Credit Payment Account (Grand Total)
    gl_entries.append(frappe.get_doc({
        "doctype": "GL Entry",
        "posting_date": expense_doc.expense_date,
        "account": expense_doc.payment_account,
        "debit": 0 if not is_cancelled else abs(flt(expense_doc.grand_total)),
        "credit": abs(flt(expense_doc.grand_total)) if not is_cancelled else 0,
        "voucher_type": "Hospitality Expense",
        "voucher_no": expense_doc.name,
        "remarks": f"Payment via {expense_doc.paid_via} for {expense_doc.name}",
        "is_cancelled": 1 if is_cancelled else 0,
        "cost_center": expense_doc.cost_center,
        "company": company
    }))

    for entry in gl_entries:
        entry.insert(ignore_permissions=True)

@frappe.whitelist()
def run_pos_cancellation_test():
    import time
    from frappe.utils import nowdate
    print("Starting POS Cancellation Fix Verification Test...")
    
    # 1. Setup Data
    company = "Edo Heritage Hotel"
    ts = str(int(time.time()))
    room_number = "101TEST"
    item_code = "TEST_BEER"
    
    if not frappe.db.exists("Hotel Room", room_number):
        frappe.get_doc({
            "doctype": "Hotel Room", 
            "room_number": room_number, 
            "status": "Available", 
            "is_group_room": 0,
            "room_type": "Classic Deluxe",
            "hotel_reception": "Old Building"
        }).insert()

    guest_name = "ZOFMON INVESTMENT"
    customer = frappe.db.get_value("Guest", guest_name, "customer")

    if not customer:
        # Fallback if specific guest doesn't have customer
        guest_name = frappe.db.get_value("Guest", {}, "name")
        customer = frappe.db.get_value("Guest", guest_name, "customer")

    if not frappe.db.exists("Item", item_code):
        frappe.get_doc({
            "doctype": "Item",
            "item_code": item_code,
            "item_name": "Test Beer",
            "item_group": "Drinks",
            "is_stock_item": 0,
            "opening_stock": 0,
            "valuation_rate": 0,
            "standard_rate": 2000
        }).insert()

    # Create Reservation & Check-in
    res = frappe.get_doc({
        "doctype": "Hotel Reservation",
        "company": company,
        "hotel_reception": "Old Building",
        "guest": guest_name,
        "room_type": "Classic Deluxe",
        "room": room_number,
        "arrival_date": nowdate(),
        "departure_date": nowdate(),
        "status": "Reserved",
        "allow_pos_posting": 1
    }).insert(ignore_permissions=True)
    res.process_check_in()
    
    folio_name = frappe.db.get_value("Guest Folio", {"reservation": res.name}, "name")
    print(f"Checkout Reservation: {res.name}, Folio: {folio_name}")

    # 2. Create POS Invoice
    pos_profile = frappe.db.get_value("POS Profile", {"company": company}, "name")
    
    pos_inv = frappe.get_doc({
        "doctype": "POS Invoice",
        "company": company,
        "customer": customer,
        "pos_profile": pos_profile,
        "posting_date": nowdate(),
        "hotel_room": room_number,
        "update_stock": 0,
        "items": [
            {
                "item_code": item_code,
                "qty": 1,
                "rate": 2450,
                "amount": 2450
            }
        ],
        "payments": [
            {
                "mode_of_payment": "Room Charge",
                "amount": 2450,
                "account": frappe.db.get_value("Mode of Payment Account", {"parent": "Room Charge", "company": company}, "default_account")
            }
        ]
    })
    
    pos_inv.insert(ignore_permissions=True)
    pos_inv.submit()
    print(f"Submitted POS Invoice: {pos_inv.name}")

    # 3. Verify GL Entries
    gl_entries = frappe.get_all("GL Entry", filters={"voucher_no": pos_inv.name, "is_cancelled": 0})
    print(f"Found {len(gl_entries)} GL entries for {pos_inv.name}")
    
    # 4. Cancel POS Invoice
    pos_inv.cancel()
    print(f"Successfully cancelled POS Invoice: {pos_inv.name}")

    # 5. Verify Reversal
    reversals = frappe.get_all("GL Entry", filters={"voucher_no": pos_inv.name, "is_cancelled": 1})
    print(f"Found {len(reversals)} reversal GL entries for {pos_inv.name}")

    if len(reversals) > 0:
        print("PASS: Reversal GL entries created.")
    else:
        print("FAIL: No reversal GL entries found.")

    # 6. Check Folio Transactions
    txn_count = frappe.db.count("Folio Transaction", {"reference_name": pos_inv.name})
    if txn_count == 0:
        print("PASS: Folio Transactions deleted upon cancellation.")
    else:
        print(f"FAIL: {txn_count} Folio Transactions still exist.")
