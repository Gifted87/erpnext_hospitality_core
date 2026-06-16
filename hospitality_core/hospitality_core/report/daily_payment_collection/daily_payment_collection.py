import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    columns = [
        {"label": _("Payment Ref"), "fieldname": "name", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 140},
        {"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Data", "width": 120, "hidden": 1},
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Mode"), "fieldname": "mode_of_payment", "fieldtype": "Data", "width": 120},
        {"label": _("Party"), "fieldname": "party_name", "fieldtype": "Data", "width": 150},
        {"label": _("Folio Ref"), "fieldname": "reference_no", "fieldtype": "Data", "width": 150},
        {"label": _("Amount"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Type"), "fieldname": "payment_type", "fieldtype": "Data", "width": 80},
        {"label": _("Poster"), "fieldname": "owner_name", "fieldtype": "Data", "width": 150}
    ]

    # Filters
    date_from = filters.get("from_date")
    date_to = filters.get("to_date")
    reception = filters.get("hotel_reception")
    poster = filters.get("poster")
    mode_of_payment = filters.get("mode_of_payment")

    conditions_pe = ""
    conditions_pi = ""

    if reception:
        conditions_pe += " AND pe.hotel_reception = %(hotel_reception)s"

    if poster:
        conditions_pe += " AND pe.owner = %(poster)s"
        conditions_pi += " AND pi.owner = %(poster)s"

    if mode_of_payment:
        conditions_pe += " AND pe.mode_of_payment = %(mode_of_payment)s"
        conditions_pi += " AND pip.mode_of_payment = %(mode_of_payment)s"

    sql = f"""
        SELECT
            pe.name,
            'Payment Entry' as voucher_type,
            pe.posting_date,
            pe.mode_of_payment,
            pe.party_name,
            pe.reference_no,
            pe.paid_amount,
            pe.payment_type,
            (SELECT full_name FROM `tabUser` WHERE name = pe.owner) as owner_name
        FROM
            `tabPayment Entry` pe
        WHERE
            pe.docstatus = 1
            AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s
            {conditions_pe}
            AND (
                pe.reference_no LIKE 'FOLIO%%' 
                OR pe.reference_no LIKE 'MASTER%%' 
                OR pe.remarks LIKE '%%Hotel%%'
                OR EXISTS (SELECT 1 FROM `tabGuest Folio` gf WHERE gf.name = pe.reference_no)
            )
            
        UNION ALL
        
        SELECT
            pi.name,
            'POS Invoice' as voucher_type,
            DATE(SUBTIME(CONCAT(pi.posting_date, ' ', IFNULL(pi.posting_time, '00:00:00')), '08:00:00')) as posting_date,
            pip.mode_of_payment,
            pi.customer_name as party_name,
            pi.name as reference_no,
            pip.amount as paid_amount,
            'Receive' as payment_type,
            (SELECT full_name FROM `tabUser` WHERE name = pi.owner) as owner_name
        FROM
            `tabPOS Invoice` pi
        JOIN
            `tabSales Invoice Payment` pip ON pip.parent = pi.name
        WHERE
            pi.docstatus = 1
            AND DATE(SUBTIME(CONCAT(pi.posting_date, ' ', IFNULL(pi.posting_time, '00:00:00')), '08:00:00')) BETWEEN %(from_date)s AND %(to_date)s
            AND pi.pos_profile IN ('Reception', 'Reception (New)')
            AND pip.mode_of_payment NOT IN ('Guest Account', 'Complimentary')
            AND pip.amount > 0
            {conditions_pi}
            
        ORDER BY
            mode_of_payment, posting_date
    """

    data = frappe.db.sql(sql, filters, as_dict=True)

    # Calculate Totals by Mode
    total_cash = sum(d.paid_amount for d in data if d.mode_of_payment and d.mode_of_payment.lower() == 'cash')
    total_card = sum(d.paid_amount for d in data if d.mode_of_payment and d.mode_of_payment.lower() != 'cash')
    total_all = sum(d.paid_amount for d in data)
    
    if data:
        data.append({"party_name": "<b>TOTAL CASH</b>", "paid_amount": total_cash})
        data.append({"party_name": "<b>TOTAL OTHER</b>", "paid_amount": total_card})
        data.append({"party_name": "<b>GRAND TOTAL</b>", "paid_amount": total_all})

    return columns, data


def _resolve_room_for_rows(rows):
    """
    Enriches each data row with a 'room' field.
    - Payment Entry rows: look up room via Guest Folio (reference_no is the folio name)
    - POS Invoice rows: use hotel_room field from POS Invoice
    """
    for row in rows:
        if row.get("room"):
            continue  # already resolved

        voucher_type = row.get("voucher_type", "")
        ref_no = row.get("reference_no", "") or ""

        if voucher_type == "Payment Entry":
            # reference_no is the Folio name
            if ref_no:
                room = frappe.db.get_value("Guest Folio", ref_no, "room")
                row["room"] = room or ""
            else:
                row["room"] = ""

        elif voucher_type == "POS Invoice":
            # reference_no is the POS Invoice name
            if ref_no:
                room = frappe.db.get_value("POS Invoice", ref_no, "hotel_room")
                row["room"] = room or ""
            else:
                row["room"] = ""
        else:
            row["room"] = ""

    return rows


@frappe.whitelist(allow_guest=False)
def print_daily_payment_collection(from_date=None, to_date=None, hotel_reception=None,
                                    poster=None, mode_of_payment=None):
    """Render and return the Daily Payment Collection print format as an HTML page."""
    filters = {}
    if from_date:
        filters["from_date"] = from_date
    if to_date:
        filters["to_date"] = to_date
    if hotel_reception:
        filters["hotel_reception"] = hotel_reception
    if poster:
        filters["poster"] = poster
    if mode_of_payment:
        filters["mode_of_payment"] = mode_of_payment

    _columns, data = execute(filters)

    # Filter out summary total rows (they have no voucher_type)
    data_rows = [r for r in data if r.get("voucher_type")]

    # Resolve room numbers
    _resolve_room_for_rows(data_rows)

    doc = frappe._dict({
        "data": data_rows,
        "from_date": from_date,
        "to_date": to_date,
    })

    template_path = frappe.get_app_path(
        "hospitality_core",
        "hospitality_core",
        "print_format",
        "daily_payment_collection_classic",
        "daily_payment_collection_classic.html",
    )
    with open(template_path, encoding="utf-8") as f:
        html_template = f.read()

    rendered_html = frappe.render_template(html_template, {"doc": doc, "frappe": frappe})

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Daily Payment Collection</title>
    <style>body {{ background: #fff; margin: 0; padding: 20px; }} @media print {{ body {{ padding: 0; }} }}</style>
</head>
<body>
    {rendered_html}
    <script>window.addEventListener("load", function() {{ setTimeout(function() {{ window.print(); }}, 300); }});</script>
</body>
</html>"""

    frappe.response["type"] = "download"
    frappe.response["filename"] = "daily-payment-collection.html"
    frappe.response["filecontent"] = html
    frappe.response["content_type"] = "text/html; charset=utf-8"
    frappe.response["display_content_as"] = "inline"