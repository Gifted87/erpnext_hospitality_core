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
        {"label": _("Gross Amount"), "fieldname": "gross_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Discount"), "fieldname": "discount_amount", "fieldtype": "Currency", "width": 100},
        {"label": _("Net Charged"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
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
    # 3. We exclude Voided transactions and Payment/Transfer items
    # 4. We include BOTH positive charges AND negative discount/complimentary credits
    #    so the net amount after discount is correctly reflected.
    
    conditions = ""
    # Filter: Exclude Companies and Complimentary if checkbox is NOT checked
    if not filters.get("include_non_revenue"):
         conditions += """
            AND (gf.is_company_master = 0 OR gf.is_company_master IS NULL)
            AND (res.is_complimentary = 0 OR res.is_complimentary IS NULL)
         """
    
    if filters.get("hotel_reception"):
        conditions += " AND (res.hotel_reception = %(hotel_reception)s OR gf.hotel_reception = %(hotel_reception)s)"
    
    # Fetch all charge and discount rows per reservation per date, grouped
    # We aggregate charges (positive) and discounts (negative) per room/guest/date/item_group
    sql = f"""
        SELECT
            ft.posting_date,
            gf.room,
            guest.full_name as guest_name,
            item.item_group,
            ft.item,
            ft.description,
            CASE WHEN ft.amount > 0 THEN ft.amount ELSE 0 END as gross_amount,
            CASE WHEN ft.amount < 0 THEN ABS(ft.amount) ELSE 0 END as discount_amount,
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
            AND (ft.reference_doctype != 'Payment Entry' OR ft.reference_doctype IS NULL)
            AND ft.item NOT IN ('PAYMENT', 'TRANSFER', 'TRANSFER-GROUP')
            {conditions}
        ORDER BY
            ft.posting_date, item.item_group
    """
    
    raw_data = frappe.db.sql(sql, filters, as_dict=True)
    
    from hospitality_core.hospitality_core.api.accounting import get_tax_breakdown
    
    charges = []
    discounts = {}
    
    # 1. Separate negative transactions (discounts) from positive charges
    for row in raw_data:
        if row.amount < 0:
            key = (row.posting_date, row.room)
            discounts[key] = discounts.get(key, 0) + row.discount_amount
        else:
            charges.append(row)
            
    # 2. Merge discounts into room charges and calculate taxes
    for row in charges:
        key = (row.posting_date, row.room)
        
        # If this is a room charge and there is a discount for this room/date
        if key in discounts and (row.item == 'ROOM-RENT' or row.item_group in ['Accommodation', 'Services']):
            row.discount_amount = discounts[key]
            row.amount = row.gross_amount - row.discount_amount
            del discounts[key] # Remove so we don't apply it twice
            
        # Calculate taxes on the net charged amount (after discount)
        taxes = get_tax_breakdown(row.amount)
        row.update({
            "net_amount": taxes["net_amount"],
            "ct_amount": taxes["ct_amount"],
            "vat_amount": taxes["vat_amount"],
            "sc_amount": taxes["sc_amount"]
        })
        
    # 3. Handle any orphaned discounts (e.g. if a discount was posted without a corresponding charge)
    for key, disc_amt in discounts.items():
        charges.append({
            "posting_date": key[0],
            "room": key[1],
            "guest_name": "Unknown",
            "item_group": "Adjustment",
            "description": "Orphaned Discount",
            "gross_amount": 0,
            "discount_amount": disc_amt,
            "amount": -disc_amt,
            "net_amount": -disc_amt,
            "ct_amount": 0,
            "vat_amount": 0,
            "sc_amount": 0
        })

    return columns, charges