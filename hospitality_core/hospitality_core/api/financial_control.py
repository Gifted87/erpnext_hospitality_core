import frappe
from frappe import _


@frappe.whitelist()
def void_transaction(folio_transaction_name, reason_code):
    """
    Voids a Folio Transaction.

    Behaviour depends on what the transaction is linked to:

    * POS Invoice  → If the invoice belongs to a submitted POS Closing Entry,
                     first cancel the closing entry, then cancel the POS Invoice.
                     The on_cancel hook (void_room_charge) deletes all linked
                     Folio Transactions and syncs the balance automatically.
                     Finally, amend the POS Closing Entry and resubmit it.
    * Payment Entry → Cancel the Payment Entry. The on_cancel hook
                      (process_payment_entry) will delete the credit Folio
                      Transaction and reverse accounting.
    * Regular (no reference, or Sales Invoice) → Mark is_void=1 in-place and
                      zero the amount so the balance is unaffected.
    """
    if not ("Frontdesk Supervisor" in frappe.get_roles() or frappe.session.user == "Administrator"):
        frappe.throw(_("Access Denied. Only Frontdesk Supervisors can void transactions."))

    # 1. Fetch Transaction
    trans = frappe.get_doc("Folio Transaction", folio_transaction_name)

    if trans.is_void:
        frappe.throw(_("Transaction is already void."))

    # 2. Check Reason Code / Approval
    reason_doc = frappe.get_doc("Allowance Reason Code", reason_code)
    if reason_doc.requires_manager_approval:
        if not ("Frontdesk Supervisor" in frappe.get_roles() or frappe.session.user == "Administrator"):
            frappe.throw(_("This Reason Code requires Supervisor Approval."))

    ref_doctype = trans.reference_doctype or ""
    ref_name = trans.reference_name or ""

    # ── POS Invoice transactions ─────────────────────────────────────────────
    if ref_doctype == "POS Invoice" and ref_name:
        pos_doc = frappe.get_doc("POS Invoice", ref_name)
        if pos_doc.docstatus == 2:
            frappe.msgprint(_(f"POS Invoice '{ref_name}' was already cancelled."))
            return
        if pos_doc.docstatus != 1:
            frappe.throw(_(f"POS Invoice '{ref_name}' is not in a submitted state and cannot be cancelled."))

        # Check if this POS Invoice belongs to a submitted POS Closing Entry
        closing_entry_name = _find_submitted_closing_entry_for_invoice(ref_name)

        if closing_entry_name:
            _void_pos_invoice_with_closing_entry(pos_doc, closing_entry_name, ref_name)
        else:
            # No consolidated closing entry — cancel directly
            # Cancelling triggers void_room_charge (on_cancel hook) which:
            #   • Deletes all linked Folio Transaction rows for this invoice
            #   • Syncs the Folio balance automatically
            pos_doc.cancel()
            frappe.db.commit()
            frappe.msgprint(
                _(f"POS Invoice '{ref_name}' cancelled — charges removed from the Folio.")
            )
        return

    # ── Payment Entry transactions ────────────────────────────────────────────
    if ref_doctype == "Payment Entry" and ref_name:
        pe_doc = frappe.get_doc("Payment Entry", ref_name)
        if pe_doc.docstatus == 2:
            frappe.msgprint(_(f"Payment Entry '{ref_name}' was already cancelled."))
            return
        if pe_doc.docstatus != 1:
            frappe.throw(_(f"Payment Entry '{ref_name}' is not in a submitted state and cannot be cancelled."))

        # Cancelling triggers process_payment_entry (on_cancel hook) which:
        #   • Deletes the credit Folio Transaction row for this payment
        #   • Reverses the accounting realization journal
        #   • Syncs the Folio balance automatically
        pe_doc.cancel()
        frappe.db.commit()
        frappe.msgprint(
            _(f"Payment Entry '{ref_name}' cancelled — credit removed from the Folio.")
        )
        return

    # ── Regular (non-linked or Sales-Invoice-linked) transactions ────────────
    if trans.is_invoiced:
        frappe.throw(_(
            "Cannot void this transaction because it has already been invoiced "
            "(Sales Invoice generated). Create a Credit Note instead."
        ))

    frappe.db.set_value("Folio Transaction", trans.name, {
        "is_void": 1,
        "void_reason": reason_code,
        "amount": 0  # Zero out so balance is correct even if filter misses it
    })
    # Commit so the write is visible to the subsequent SQL in sync_folio_balance
    frappe.db.commit()

    from hospitality_core.hospitality_core.api.folio import sync_folio_balance
    folio_doc = frappe.get_doc("Guest Folio", trans.parent)
    sync_folio_balance(folio_doc)

    frappe.msgprint(_(f"Transaction '{trans.description}' voided successfully."))


def _find_submitted_closing_entry_for_invoice(pos_invoice_name):
    """
    Returns the name of the submitted POS Closing Entry that references
    the given POS Invoice, or None if not found.
    """
    result = frappe.db.sql(
        """
        SELECT pce.name
        FROM `tabPOS Closing Entry` pce
        INNER JOIN `tabPOS Invoice Reference` pir ON pir.parent = pce.name
        WHERE pce.docstatus = 1
          AND pir.pos_invoice = %(invoice)s
        LIMIT 1
        """,
        {"invoice": pos_invoice_name},
        as_dict=True,
    )
    if result:
        return result[0].name
    return None


def _void_pos_invoice_with_closing_entry(pos_doc, closing_entry_name, ref_name):
    """
    Handles voiding a POS Invoice that belongs to a submitted POS Closing Entry.

    Workflow:
    1. Cancel the POS Closing Entry
    2. Cancel the POS Invoice  (on_cancel hook removes Folio Transactions)
    3. Amend the POS Closing Entry (creates a new draft without the voided invoice)
    4. Submit the amended POS Closing Entry
    """
    frappe.msgprint(
        _(
            f"POS Invoice '{ref_name}' is part of POS Closing Entry '{closing_entry_name}'. "
            "Cancelling closing entry, voiding invoice, and resubmitting amended closing entry…"
        )
    )

    # ── Step 1: Cancel the POS Closing Entry ─────────────────────────────────
    closing_doc = frappe.get_doc("POS Closing Entry", closing_entry_name)
    if closing_doc.docstatus != 1:
        frappe.throw(_(f"POS Closing Entry '{closing_entry_name}' is not submitted. Cannot proceed."))

    try:
        closing_doc.cancel()
        frappe.db.commit()
    except Exception as e:
        frappe.throw(_(f"Failed to cancel POS Closing Entry '{closing_entry_name}': {str(e)}"))

    # ── Step 2: Cancel the POS Invoice ───────────────────────────────────────
    # (triggers void_room_charge on_cancel hook → removes Folio Transaction rows)
    try:
        pos_doc.reload()
        pos_doc.cancel()
        frappe.db.commit()
    except Exception as e:
        frappe.throw(_(f"Failed to cancel POS Invoice '{ref_name}': {str(e)}"))

    frappe.msgprint(_(f"POS Invoice '{ref_name}' cancelled — charges removed from the Folio."))

    # ── Step 3: Amend the POS Closing Entry ──────────────────────────────────
    try:
        amended_closing = frappe.copy_doc(closing_doc)
        amended_closing.amended_from = closing_entry_name
        amended_closing.docstatus = 0

        # Remove the voided invoice from the pos_transactions child table
        amended_closing.pos_transactions = [
            row for row in (amended_closing.pos_transactions or [])
            if row.pos_invoice != ref_name
        ]

        # Recalculate totals from remaining invoices
        _recalculate_closing_entry_totals(amended_closing)

        amended_closing.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.throw(_(
            f"POS Invoice was voided but amending POS Closing Entry '{closing_entry_name}' "
            f"failed: {str(e)}. Please manually amend the closing entry."
        ))

    # ── Step 4: Submit the amended POS Closing Entry ─────────────────────────
    try:
        amended_closing.submit()
        frappe.db.commit()
    except Exception as e:
        frappe.throw(_(
            f"POS Invoice was voided but submitting amended POS Closing Entry failed: {str(e)}. "
            f"Draft '{amended_closing.name}' was created — please submit it manually."
        ))

    frappe.msgprint(
        _(
            f"Done. POS Invoice '{ref_name}' voided. "
            f"POS Closing Entry amended and resubmitted as '{amended_closing.name}'."
        )
    )


def _recalculate_closing_entry_totals(closing_doc):
    """
    Recalculates grand_total, net_total, total_quantity and payment_reconciliation
    on an amended POS Closing Entry based on the remaining pos_transactions rows.
    """
    if not closing_doc.pos_transactions:
        closing_doc.grand_total = 0
        closing_doc.net_total = 0
        closing_doc.total_quantity = 0
        if hasattr(closing_doc, "payment_reconciliation"):
            for row in closing_doc.payment_reconciliation:
                row.expected_amount = 0
                row.opening_amount = 0
                row.closing_amount = 0
        return

    remaining_names = tuple(r.pos_invoice for r in closing_doc.pos_transactions)

    # Recalculate grand/net totals from remaining submitted invoices
    totals = frappe.db.sql(
        """
        SELECT
            COALESCE(SUM(grand_total), 0)  AS grand_total,
            COALESCE(SUM(net_total), 0)    AS net_total,
            COALESCE(SUM(total_qty), 0)    AS total_quantity
        FROM `tabPOS Invoice`
        WHERE name IN %(names)s
          AND docstatus = 1
        """,
        {"names": remaining_names},
        as_dict=True,
    )
    if totals:
        closing_doc.grand_total = totals[0].grand_total
        closing_doc.net_total = totals[0].net_total
        closing_doc.total_quantity = totals[0].total_quantity

    # Recalculate payment_reconciliation expected amounts
    payment_rows = frappe.db.sql(
        """
        SELECT
            sip.mode_of_payment,
            COALESCE(SUM(sip.amount), 0) AS expected_amount
        FROM `tabSales Invoice Payment` sip
        INNER JOIN `tabPOS Invoice` pi ON pi.name = sip.parent
        WHERE sip.parent IN %(names)s
          AND pi.docstatus = 1
        GROUP BY sip.mode_of_payment
        """,
        {"names": remaining_names},
        as_dict=True,
    )
    payment_map = {row.mode_of_payment: row.expected_amount for row in payment_rows}

    if hasattr(closing_doc, "payment_reconciliation"):
        for row in closing_doc.payment_reconciliation:
            row.expected_amount = payment_map.get(row.mode_of_payment, 0)
            row.opening_amount = 0
            row.closing_amount = row.expected_amount