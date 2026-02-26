import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    columns = [
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Room"), "fieldname": "room", "fieldtype": "Data", "width": 80},
        {"label": _("Guest"), "fieldname": "guest_name", "fieldtype": "Data", "width": 150},
        {"label": _("Department / Item Group"), "fieldname": "item_group", "fieldtype": "Data", "width": 150},
        {"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 200},
        {"label": _("Gross Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Net Amount"), "fieldname": "net_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("CT (5%)"), "fieldname": "ct_amount", "fieldtype": "Currency", "width": 100},
        {"label": _("VAT (7.5%)"), "fieldname": "vat_amount", "fieldtype": "Currency", "width": 100},
        {"label": _("SC (10%)"), "fieldname": "sc_amount", "fieldtype": "Currency", "width": 100}
    ]

    # Filters
    date_from = filters.get("from_date")
    date_to = filters.get("to_date")

    # SQL Logic:
    # 1. We query `Folio Transaction`
    # 2. We join `Item` to get the Item Group (Department)
    # 3. We exclude Voided transactions and Payments (Amount < 0)
    
    conditions = ""
    # Filter: Exclude Companies and Complimentary if checkbox is NOT checked
    if not filters.get("include_non_revenue"):
         conditions += """
            AND (gf.is_company_master = 0 OR gf.is_company_master IS NULL)
            AND (res.is_complimentary = 0 OR res.is_complimentary IS NULL)
         """
    
    if filters.get("hotel_reception"):
        conditions += " AND (res.hotel_reception = %(hotel_reception)s OR gf.hotel_reception = %(hotel_reception)s)"
    
    sql = f"""
        SELECT
            ft.posting_date,
            gf.room,
            guest.full_name as guest_name,
            item.item_group,
            ft.description,
            ft.amount
        FROM
            `tabFolio Transaction` ft
        INNER JOIN
            `tabGuest Folio` gf ON ft.parent = gf.name
        LEFT JOIN
            `tabGuest` guest ON gf.guest = guest.name
        LEFT JOIN
            `tabHotel Reservation` res ON gf.reservation = res.name
        LEFT JOIN
            `tabItem` item ON ft.item = item.name
        WHERE
            ft.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND ft.is_void = 0
            AND ft.amount > 0 
            {conditions}
        ORDER BY
            ft.posting_date, item.item_group
    """
    
    data = frappe.db.sql(sql, filters, as_dict=True)
    
    from hospitality_core.hospitality_core.api.accounting import get_tax_breakdown
    
    for row in data:
        taxes = get_tax_breakdown(row.amount)
        row.update({
            "net_amount": taxes["net_amount"],
            "ct_amount": taxes["ct_amount"],
            "vat_amount": taxes["vat_amount"],
            "sc_amount": taxes["sc_amount"]
        })

    return columns, data