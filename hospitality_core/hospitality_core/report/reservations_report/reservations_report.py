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
        {"label": _("Reservation"), "fieldname": "name", "fieldtype": "Link", "options": "Hotel Reservation", "width": 150},
        {"label": _("Room"), "fieldname": "room", "fieldtype": "Link", "options": "Hotel Room", "width": 80},
        {"label": _("Room Type"), "fieldname": "room_type", "fieldtype": "Link", "options": "Hotel Room Type", "width": 120},
        {"label": _("Guest"), "fieldname": "guest_name", "fieldtype": "Data", "width": 180},
        {"label": _("Billing Type"), "fieldname": "billing_type", "fieldtype": "Data", "width": 140},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
        {"label": _("Arrival Date"), "fieldname": "arrival_date", "fieldtype": "Date", "width": 110},
        {"label": _("Departure Date"), "fieldname": "departure_date", "fieldtype": "Date", "width": 110},
        {"label": _("Nights"), "fieldname": "nights", "fieldtype": "Int", "width": 70},
        {"label": _("Rate Plan"), "fieldname": "rate_plan", "fieldtype": "Link", "options": "Rate Plan", "width": 130},
        {"label": _("Folio"), "fieldname": "folio", "fieldtype": "Link", "options": "Guest Folio", "width": 140},
        {"label": _("Booked By"), "fieldname": "reserved_by", "fieldtype": "Data", "width": 130},
    ]


def get_data(filters):
    target_date = filters.get("date") or nowdate()
    view_mode = filters.get("view_mode") or "Arrivals"

    conditions = []
    params = {"target_date": target_date}

    if view_mode == "Arrivals":
        # Reservations arriving on selected date
        conditions.append("res.arrival_date = %(target_date)s")
    elif view_mode == "Departures":
        # Reservations departing on selected date
        conditions.append("res.departure_date = %(target_date)s")
    elif view_mode == "In-House":
        # All guests in-house on selected date (arrived on or before, departing after)
        conditions.append("res.arrival_date <= %(target_date)s")
        conditions.append("res.departure_date > %(target_date)s")
    else:
        # Default: arrivals
        conditions.append("res.arrival_date = %(target_date)s")

    if filters.get("status"):
        conditions.append("res.status = %(status)s")
        params["status"] = filters.get("status")

    if filters.get("hotel_reception"):
        conditions.append("res.hotel_reception = %(hotel_reception)s")
        params["hotel_reception"] = filters.get("hotel_reception")

    if filters.get("room_type"):
        conditions.append("res.room_type = %(room_type)s")
        params["room_type"] = filters.get("room_type")

    where_clause = " AND ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT
            res.name,
            res.room,
            res.room_type,
            COALESCE(g.full_name, res.guest) AS guest_name,
            res.is_complimentary,
            res.is_company_guest,
            res.is_group_guest,
            res.company,
            res.status,
            res.arrival_date,
            res.departure_date,
            DATEDIFF(res.departure_date, res.arrival_date) AS nights,
            res.rate_plan,
            res.folio,
            u.full_name AS reserved_by
        FROM `tabHotel Reservation` res
        LEFT JOIN `tabGuest` g ON g.name = res.guest
        LEFT JOIN `tabUser` u ON u.name = res.reserved_by
        WHERE {where_clause}
        ORDER BY
            CASE WHEN res.room REGEXP '^[0-9]+$' THEN 0 ELSE 1 END,
            CAST(res.room AS UNSIGNED),
            res.room ASC,
            res.arrival_date ASC
        """,
        params,
        as_dict=True,
    )

    for row in rows:
        row["billing_type"] = _get_billing_label(row)

    return rows


def _get_billing_label(row):
    """
    Returns a human-readable billing/guest type label.
    Priority: Complimentary > Company Guest > Group Guest > Individual
    """
    if row.get("is_complimentary"):
        return "Complimentary"
    if row.get("is_company_guest") and row.get("company"):
        return f"Company — {row['company']}"
    if row.get("is_group_guest"):
        return "Group"
    return "Individual"
