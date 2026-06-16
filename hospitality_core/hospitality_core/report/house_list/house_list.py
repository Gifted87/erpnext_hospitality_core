import frappe
from frappe import _
from frappe.utils import getdate, nowdate

def execute(filters=None):
    if not filters:
        filters = {}
        
    target_date = filters.get("date") or nowdate()
    
    columns = [
        {"label": _("Room"), "fieldname": "room", "fieldtype": "Link", "options": "Hotel Room", "width": 80},
        {"label": _("Guest Name"), "fieldname": "guest_name", "fieldtype": "Data", "width": 150},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": _("Arrival"), "fieldname": "arrival_date", "fieldtype": "Date", "width": 100},
        {"label": _("Departure"), "fieldname": "departure_date", "fieldtype": "Date", "width": 100},
        {"label": _("Rate Plan"), "fieldname": "rate_plan", "fieldtype": "Data", "width": 120},
        {"label": _("Pax"), "fieldname": "pax", "fieldtype": "Data", "width": 60, "default": "1"}, # Adults/Children
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": _("Balance Due"), "fieldname": "balance_due", "fieldtype": "Currency", "width": 110},
        {"label": _("Credit"), "fieldname": "excess_payment", "fieldtype": "Currency", "width": 110}
    ]

    sql = """
        SELECT 
            res.room,
            guest.full_name as guest_name,
            res.status,
            res.arrival_date,
            res.departure_date,
            res.rate_plan,
            res.company,
            CASE WHEN folio.outstanding_balance > 0 THEN folio.outstanding_balance ELSE 0 END as balance_due,
            folio.excess_payment
        FROM
            `tabHotel Reservation` res
        LEFT JOIN
            `tabGuest` guest ON res.guest = guest.name
        LEFT JOIN
            `tabGuest Folio` folio ON res.folio = folio.name
        WHERE
            res.arrival_date <= %(date)s
            AND res.departure_date > %(date)s
            AND res.status IN ('Checked In', 'Checked Out')
        ORDER BY
            CASE WHEN res.room REGEXP '^[0-9]+$' THEN 0 ELSE 1 END,
            CAST(res.room AS UNSIGNED),
            res.room
    """

    data = frappe.db.sql(sql, {"date": target_date}, as_dict=True)
    
    # Add Total Rooms Occupied count
    report_summary = []
    if data:
        report_summary = [
            {"value": len(data), "label": _("Total Occupied Rooms"), "datatype": "Int"},
        ]

    return columns, data, None, None, report_summary

@frappe.whitelist(allow_guest=False)
def print_house_list(date=None):
    if not date:
        date = nowdate()
        
    columns, data, _, _, report_summary = execute({"date": date})
    
    # We create a dummy doc object to pass to the jinja template
    doc = frappe._dict({
        "date": date,
        "data": data,
        "summary": report_summary
    })
    
    template_path = frappe.get_app_path(
        "hospitality_core",
        "hospitality_core",
        "print_format",
        "house_list_classic",
        "house_list_classic.html",
    )
    with open(template_path, encoding="utf-8") as template_file:
        html_template = template_file.read()

    rendered_html = frappe.render_template(html_template, {"doc": doc, "frappe": frappe})
    
    # Return it wrapped in standard print view styling
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Print House List</title>
        <style>
            body {{ background: #fff; margin: 0; padding: 20px; }}
            @media print {{
                body {{ padding: 0; }}
            }}
        </style>
    </head>
    <body>
        {rendered_html}
        <script>
            window.addEventListener("load", function() {{
                setTimeout(function() {{ window.print(); }}, 300);
            }});
        </script>
    </body>
    </html>
    """

    frappe.response["type"] = "download"
    frappe.response["filename"] = "house-list.html"
    frappe.response["filecontent"] = html
    frappe.response["content_type"] = "text/html; charset=utf-8"
    frappe.response["display_content_as"] = "inline"
