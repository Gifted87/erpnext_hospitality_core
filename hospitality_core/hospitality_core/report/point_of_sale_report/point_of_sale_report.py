import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 220},
        {"label": _("Qty Sold"), "fieldname": "qty_sold", "fieldtype": "Float", "width": 120},
        {"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140},
    ]

    if not filters.get("pos_profile"):
        return columns, []

    date_cond = ""
    if filters.get("from_date") and filters.get("to_date"):
        date_cond = "AND pos.posting_date BETWEEN %(from_date)s AND %(to_date)s"

    # --- Item rows ---
    data = frappe.db.sql(
        f"""
        SELECT
            item.item_name,
            SUM(item.qty) AS qty_sold,
            SUM(item.amount) AS amount
        FROM `tabPOS Invoice` pos
        INNER JOIN `tabPOS Invoice Item` item ON item.parent = pos.name
        WHERE
            pos.docstatus = 1
            AND pos.status = 'Paid'
            AND pos.pos_profile = %(pos_profile)s
            {date_cond}
        GROUP BY item.item_name
        ORDER BY amount DESC
        """,
        filters,
        as_dict=True,
    )

    total_qty = sum(flt(r.qty_sold) for r in data)
    total_amount = sum(flt(r.amount) for r in data)

    # --- Total row ---
    data.append({
        "item_name": f"<b>{_('Total')}</b>",
        "qty_sold": total_qty,
        "amount": total_amount,
    })

    # --- Blank separator ---
    data.append({"item_name": "", "qty_sold": None, "amount": None})

    # --- Payment method breakdown header ---
    data.append({
        "item_name": f"<b>{_('Collected by Payment Method')}</b>",
        "qty_sold": None,
        "amount": None,
    })

    # --- Payment method rows ---
    payment_rows = frappe.db.sql(
        f"""
        SELECT
            pay.mode_of_payment,
            SUM(pay.amount) AS amount
        FROM `tabPOS Invoice` pos
        INNER JOIN `tabSales Invoice Payment` pay ON pay.parent = pos.name
        WHERE
            pos.docstatus = 1
            AND pos.status = 'Paid'
            AND pos.pos_profile = %(pos_profile)s
            {date_cond}
        GROUP BY pay.mode_of_payment
        ORDER BY amount DESC
        """,
        filters,
        as_dict=True,
    )

    for row in payment_rows:
        data.append({
            "item_name": row.mode_of_payment,
            "qty_sold": None,
            "amount": flt(row.amount),
        })

    return columns, data
