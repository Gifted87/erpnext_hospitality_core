import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Room"), "fieldname": "room", "fieldtype": "Link", "options": "Hotel Room", "width": 90},
		{"label": _("Room Type"), "fieldname": "room_type", "fieldtype": "Link", "options": "Hotel Room Type", "width": 120},
		{"label": _("Guest"), "fieldname": "guest_name", "fieldtype": "Data", "width": 180},
		{"label": _("Reservation"), "fieldname": "reservation", "fieldtype": "Link", "options": "Hotel Reservation", "width": 140},
		{"label": _("Folio"), "fieldname": "folio", "fieldtype": "Link", "options": "Guest Folio", "width": 140},
		{"label": _("Room Rent"), "fieldname": "room_rent", "fieldtype": "Currency", "width": 120},
		{"label": _("Discount"), "fieldname": "discount", "fieldtype": "Currency", "width": 120},
		{"label": _("Net Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	# NOTE: We do NOT filter by res.status here.
	# A reservation may be 'Checked Out' but still had ROOM-RENT posted on the
	# selected date range — those rows must appear in the sales report.
	# The date filter on ft.posting_date is the single source of truth.
	conditions = []
	params = {}

	if filters.get("from_date"):
		conditions.append("ft.posting_date >= %(from_date)s")
		params["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("ft.posting_date <= %(to_date)s")
		params["to_date"] = filters.get("to_date")

	if filters.get("hotel_reception"):
		conditions.append("res.hotel_reception = %(hotel_reception)s")
		params["hotel_reception"] = filters.get("hotel_reception")

	where_clause = (" AND " + " AND ".join(conditions)) if conditions else ""

	rows = frappe.db.sql(
		f"""
		SELECT
			res.room,
			res.room_type,
			COALESCE(g.full_name, res.guest) AS guest_name,
			res.name AS reservation,
			res.folio,
			SUM(CASE WHEN ft.item = 'ROOM-RENT' AND ft.amount > 0 THEN ft.amount ELSE 0 END) AS room_rent,
			ABS(SUM(CASE WHEN ft.item IN ('DISCOUNT', 'COMPLIMENTARY') AND ft.amount < 0 THEN ft.amount ELSE 0 END)) AS discount
		FROM `tabHotel Reservation` res
		INNER JOIN `tabGuest Folio` gf ON gf.name = res.folio
		INNER JOIN `tabFolio Transaction` ft ON ft.parent = gf.name
		LEFT JOIN `tabGuest` g ON g.name = res.guest
		WHERE
			ft.is_void = 0
			AND ft.item IN ('ROOM-RENT', 'DISCOUNT', 'COMPLIMENTARY')
			{where_clause}
		GROUP BY
			res.name, res.room, res.room_type, g.full_name, res.guest, res.folio
		HAVING
			room_rent != 0 OR discount != 0
		ORDER BY
			CASE WHEN res.room REGEXP '^[0-9]+$' THEN 0 ELSE 1 END,
			CAST(res.room AS UNSIGNED),
			res.room ASC
		""",
		params,
		as_dict=True,
	)

	total_rent = 0
	total_discount = 0
	total_amount = 0

	for row in rows:
		row.room_rent = flt(row.room_rent)
		row.discount = flt(row.discount)
		row.amount = row.room_rent - row.discount
		total_rent += row.room_rent
		total_discount += row.discount
		total_amount += row.amount

	if rows:
		rows.append(
			{
				"guest_name": "<b>Total</b>",
				"room_rent": total_rent,
				"discount": total_discount,
				"amount": total_amount,
			}
		)

	return rows


@frappe.whitelist(allow_guest=False)
def print_room_only_sales(from_date=None, to_date=None, hotel_reception=None):
	"""Render and return the Room Only Sales print format as an HTML page."""
	filters = {}
	if from_date:
		filters["from_date"] = from_date
	if to_date:
		filters["to_date"] = to_date
	if hotel_reception:
		filters["hotel_reception"] = hotel_reception

	rows = get_data(filters)

	# Separate total row from data rows
	data_rows = [r for r in rows if r.get("room")]
	total_rent = flt(sum(r.get("room_rent", 0) for r in data_rows))
	total_discount = flt(sum(r.get("discount", 0) for r in data_rows))
	total_amount = flt(sum(r.get("amount", 0) for r in data_rows))

	doc = frappe._dict({
		"data": data_rows,
		"from_date": from_date,
		"to_date": to_date,
		"total_rent": total_rent,
		"total_discount": total_discount,
		"total_amount": total_amount,
	})

	template_path = frappe.get_app_path(
		"hospitality_core",
		"hospitality_core",
		"print_format",
		"room_only_sales_classic",
		"room_only_sales_classic.html",
	)
	with open(template_path, encoding="utf-8") as f:
		html_template = f.read()

	rendered_html = frappe.render_template(html_template, {"doc": doc, "frappe": frappe})

	html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Room Only Sales</title>
    <style>body {{ background: #fff; margin: 0; padding: 20px; }} @media print {{ body {{ padding: 0; }} }}</style>
</head>
<body>
    {rendered_html}
    <script>window.addEventListener("load", function() {{ setTimeout(function() {{ window.print(); }}, 300); }});</script>
</body>
</html>"""

	frappe.response["type"] = "download"
	frappe.response["filename"] = "room-only-sales.html"
	frappe.response["filecontent"] = html
	frappe.response["content_type"] = "text/html; charset=utf-8"
	frappe.response["display_content_as"] = "inline"
