import frappe
from frappe import _
from frappe.utils import nowdate


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Room"), "fieldname": "room", "fieldtype": "Link", "options": "Hotel Room", "width": 80},
        {"label": _("Room Type"), "fieldname": "room_type", "fieldtype": "Link", "options": "Hotel Room Type", "width": 120},
        {"label": _("Guest"), "fieldname": "guest_name", "fieldtype": "Data", "width": 180},
        {"label": _("Billing Type"), "fieldname": "billing_type", "fieldtype": "Data", "width": 140},
        {"label": _("Reservation"), "fieldname": "reservation", "fieldtype": "Link", "options": "Hotel Reservation", "width": 150},
        {"label": _("Folio"), "fieldname": "folio", "fieldtype": "Link", "options": "Guest Folio", "width": 140},
        {"label": _("Arrival Date"), "fieldname": "arrival_date", "fieldtype": "Date", "width": 110},
        {"label": _("Departure Date"), "fieldname": "departure_date", "fieldtype": "Date", "width": 110},
    ]


def get_data(filters):
    conditions = "res.status = 'Checked In'"
    params = {}

    if filters.get("hotel_reception"):
        conditions += " AND res.hotel_reception = %(hotel_reception)s"
        params["hotel_reception"] = filters.get("hotel_reception")

    if filters.get("room_type"):
        conditions += " AND res.room_type = %(room_type)s"
        params["room_type"] = filters.get("room_type")

    rows = frappe.db.sql(
        """
        SELECT
            res.room,
            res.room_type,
            COALESCE(g.full_name, res.guest) AS guest_name,
            res.is_complimentary,
            res.is_company_guest,
            res.is_group_guest,
            res.company,
            res.name AS reservation,
            res.folio,
            res.arrival_date,
            res.departure_date
        FROM `tabHotel Reservation` res
        LEFT JOIN `tabGuest` g ON g.name = res.guest
        WHERE {conditions}
        ORDER BY
            CASE WHEN res.room REGEXP '^[0-9]+$' THEN 0 ELSE 1 END,
            CAST(res.room AS UNSIGNED),
            res.room ASC
        """.format(conditions=conditions),
        params,
        as_dict=True,
    )

    for row in rows:
        row["billing_type"] = _get_billing_label(row)

    return rows


def _get_billing_label(row):
    """
    Returns a human-readable billing/guest type label mirroring the house list print format.
    Priority: Complimentary > Company Guest > Group Guest > Individual
    """
    if row.get("is_complimentary"):
        return "Complimentary"
    if row.get("is_company_guest") and row.get("company"):
        return "Company - {}".format(row["company"])
    if row.get("is_group_guest"):
        return "Group"
    return "Individual"


@frappe.whitelist(allow_guest=False)
def print_guest_list(hotel_reception=None, room_type=None):
    """Render and return the Guest List print format as an HTML page."""
    filters = {}
    if hotel_reception:
        filters["hotel_reception"] = hotel_reception
    if room_type:
        filters["room_type"] = room_type

    data = get_data(filters)

    doc = frappe._dict({
        "data": data,
    })

    template_path = frappe.get_app_path(
        "hospitality_core",
        "hospitality_core",
        "print_format",
        "guest_list_classic",
        "guest_list_classic.html",
    )
    with open(template_path, encoding="utf-8") as f:
        html_template = f.read()

    rendered_html = frappe.render_template(html_template, {"doc": doc, "frappe": frappe})

    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Guest List</title>
    <style>body {{ background: #fff; margin: 0; padding: 20px; }} @media print {{ body {{ padding: 0; }} }}</style>
</head>
<body>
    {content}
    <script>window.addEventListener("load", function() {{ setTimeout(function() {{ window.print(); }}, 300); }});</script>
</body>
</html>""".format(content=rendered_html)

    frappe.response["type"] = "download"
    frappe.response["filename"] = "guest-list.html"
    frappe.response["filecontent"] = html
    frappe.response["content_type"] = "text/html; charset=utf-8"
    frappe.response["display_content_as"] = "inline"
