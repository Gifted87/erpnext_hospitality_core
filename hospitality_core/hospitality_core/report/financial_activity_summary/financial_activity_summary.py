import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

# ─── Protein item name keywords (case-insensitive LIKE match) ─────────────────
PROTEIN_KEYWORDS = ["Goatmeat", "Catfish", "Turkey", "Chicken", "Beef"]

# ─── Item groups ──────────────────────────────────────────────────────────────
DRINKS_GROUP     = "Drinks"
FOOD_GROUP       = "Food"
GYM_GROUP        = "Gym"
LAUNDRY_GROUP    = "Laundry"
SWIMMING_GROUP   = "Swimming"
PHOTOSHOOT_GROUP = "Photoshoot"
TRAY_CHARGE_NAME = "Tray Charge"


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"label": _("Description"), "fieldname": "description", "fieldtype": "Data",     "width": 280},
        {"label": _("Amount"),      "fieldname": "amount",      "fieldtype": "Currency",  "width": 160},
    ]

    if not filters.get("date"):
        return columns, []

    date = filters["date"]
    closing_entry_names = _get_closing_entry_names(date)

    # ── 1. Accommodation ──────────────────────────────────────────────────────
    accommodation = _get_room_rent_total(date)

    # ── 2–10. POS Item category sales ─────────────────────────────────────────
    drinks            = _get_item_group_total(closing_entry_names, DRINKS_GROUP)
    food_no_protein   = _get_food_without_proteins(closing_entry_names)
    goatmeat          = _get_protein_total(closing_entry_names, "Goatmeat")
    catfish           = _get_protein_total(closing_entry_names, "Catfish")
    turkey            = _get_protein_total(closing_entry_names, "Turkey")
    chicken           = _get_protein_total(closing_entry_names, "Chicken")
    beef              = _get_protein_total(closing_entry_names, "Beef")
    total_proteins    = goatmeat + catfish + turkey + chicken + beef
    food_with_protein = food_no_protein + total_proteins

    # ── 11–15. Other POS categories ───────────────────────────────────────────
    gym               = _get_item_group_total(closing_entry_names, GYM_GROUP)
    laundry           = _get_item_group_total(closing_entry_names, LAUNDRY_GROUP)
    swimming          = _get_item_group_total(closing_entry_names, SWIMMING_GROUP)
    photoshoot        = _get_item_group_total(closing_entry_names, PHOTOSHOOT_GROUP)
    tray_charge       = _get_item_name_total(closing_entry_names, TRAY_CHARGE_NAME)

    total_sales = (
        accommodation + drinks + food_with_protein +
        gym + laundry + swimming + photoshoot + tray_charge
    )

    # ── Receipts ──────────────────────────────────────────────────────────────
    from hospitality_core.hospitality_core.report.pos_sales_summary.pos_sales_summary import (
        get_closing_entries as get_pos_closing_entries,
        get_payment_map,
        get_profile_totals,
        build_summary_section
    )
    
    closing_entries = get_pos_closing_entries({"date": date})
    payment_map = get_payment_map([e.name for e in closing_entries]) if closing_entries else {}
    profile_totals = get_profile_totals(closing_entries, payment_map)
    receipts_summary = build_summary_section({"date": date}, profile_totals, no_profile_filter=True)

    # ── Build rows ────────────────────────────────────────────────────────────
    data = [
        {"description": _("<b>SALES</b>"),                "amount": None},
        {"description": _("Accommodation"),               "amount": accommodation},
        {"description": _("Drinks"),                      "amount": drinks},
        {"description": _("Food (without Proteins)"),     "amount": food_no_protein},
        {"description": _("Goatmeat"),                    "amount": goatmeat},
        {"description": _("Catfish"),                     "amount": catfish},
        {"description": _("Turkey"),                      "amount": turkey},
        {"description": _("Chicken"),                     "amount": chicken},
        {"description": _("Beef"),                        "amount": beef},
        {"description": _("<b>Total Proteins</b>"),       "amount": total_proteins},
        {"description": _("<b>Food with Proteins</b>"),   "amount": food_with_protein},
        {"description": _("Gym"),                         "amount": gym},
        {"description": _("Laundry"),                     "amount": laundry},
        {"description": _("Swimming"),                    "amount": swimming},
        {"description": _("Photoshoot"),                  "amount": photoshoot},
        {"description": _("Tray Charge"),                 "amount": tray_charge},
        {"description": "",                               "amount": None},
        {"description": _("<b>Total Sales</b>"),          "amount": total_sales},
        {"description": "",                               "amount": None},
        {"description": _("<b>RECEIPTS</b>"),             "amount": None},
    ]
    
    data.extend(receipts_summary)

    return columns, data


# ─── Private helpers ──────────────────────────────────────────────────────────

def _get_closing_entry_names(date):
    """
    Returns names of POS Closing Entries submitted on date+1
    (i.e., closing entries for the given business day).
    """
    closing_date = add_days(getdate(date), 1)
    rows = frappe.db.sql(
        """
        SELECT name FROM `tabPOS Closing Entry`
        WHERE docstatus = 1
          AND posting_date = %(closing_date)s
        """,
        {"closing_date": closing_date},
        as_dict=True,
    )
    return [r.name for r in rows] if rows else []


def _get_room_rent_total(date):
    """
    Returns total room-only sales for the given date
    by calling the exact logic from the room_only_sales report.
    """
    from hospitality_core.hospitality_core.report.room_only_sales.room_only_sales import get_data as get_room_sales_data

    sales_rows = get_room_sales_data({"from_date": date, "to_date": date})
    # The last row is the total row if there are records
    return flt(sales_rows[-1]["amount"]) if sales_rows else 0.0


def _get_item_group_total(closing_entry_names, item_group):
    """Sum POS invoice item amounts for a specific item group across closing entries."""
    if not closing_entry_names:
        return 0.0
    result = frappe.db.sql(
        """
        SELECT COALESCE(SUM(pii.amount), 0) AS total
        FROM `tabPOS Invoice Reference` pir
        INNER JOIN `tabPOS Invoice` pi ON pi.name = pir.pos_invoice
        INNER JOIN `tabPOS Invoice Item` pii ON pii.parent = pi.name
        LEFT JOIN `tabItem` it ON it.name = pii.item_code
        WHERE pir.parent IN %(names)s
          AND pi.docstatus = 1
          AND COALESCE(it.item_group, '') = %(group)s
        """,
        {"names": tuple(closing_entry_names), "group": item_group},
        as_dict=True,
    )
    return flt(result[0].total) if result else 0.0


def _get_protein_total(closing_entry_names, keyword):
    """Sum POS invoice item amounts where item_name contains the protein keyword."""
    if not closing_entry_names:
        return 0.0
    result = frappe.db.sql(
        """
        SELECT COALESCE(SUM(pii.amount), 0) AS total
        FROM `tabPOS Invoice Reference` pir
        INNER JOIN `tabPOS Invoice` pi ON pi.name = pir.pos_invoice
        INNER JOIN `tabPOS Invoice Item` pii ON pii.parent = pi.name
        WHERE pir.parent IN %(names)s
          AND pi.docstatus = 1
          AND pii.item_name LIKE %(keyword)s
        """,
        {"names": tuple(closing_entry_names), "keyword": f"%{keyword}%"},
        as_dict=True,
    )
    return flt(result[0].total) if result else 0.0


def _get_food_without_proteins(closing_entry_names):
    """
    Sum items in the Food item group that do NOT match any protein keyword.
    """
    if not closing_entry_names:
        return 0.0

    # Build exclusion conditions dynamically
    protein_conditions = " AND ".join(
        [f"pii.item_name NOT LIKE %(protein_{i})s" for i, _ in enumerate(PROTEIN_KEYWORDS)]
    )
    params = {"names": tuple(closing_entry_names), "group": FOOD_GROUP}
    for i, kw in enumerate(PROTEIN_KEYWORDS):
        params[f"protein_{i}"] = f"%{kw}%"

    result = frappe.db.sql(
        f"""
        SELECT COALESCE(SUM(pii.amount), 0) AS total
        FROM `tabPOS Invoice Reference` pir
        INNER JOIN `tabPOS Invoice` pi ON pi.name = pir.pos_invoice
        INNER JOIN `tabPOS Invoice Item` pii ON pii.parent = pi.name
        LEFT JOIN `tabItem` it ON it.name = pii.item_code
        WHERE pir.parent IN %(names)s
          AND pi.docstatus = 1
          AND COALESCE(it.item_group, '') = %(group)s
          AND {protein_conditions}
        """,
        params,
        as_dict=True,
    )
    return flt(result[0].total) if result else 0.0


def _get_item_name_total(closing_entry_names, item_name_keyword):
    """Sum items whose item_name contains the given keyword (e.g. 'Tray Charge')."""
    if not closing_entry_names:
        return 0.0
    result = frappe.db.sql(
        """
        SELECT COALESCE(SUM(pii.amount), 0) AS total
        FROM `tabPOS Invoice Reference` pir
        INNER JOIN `tabPOS Invoice` pi ON pi.name = pir.pos_invoice
        INNER JOIN `tabPOS Invoice Item` pii ON pii.parent = pi.name
        WHERE pir.parent IN %(names)s
          AND pi.docstatus = 1
          AND pii.item_name LIKE %(keyword)s
        """,
        {"names": tuple(closing_entry_names), "keyword": f"%{item_name_keyword}%"},
        as_dict=True,
    )
    return flt(result[0].total) if result else 0.0


