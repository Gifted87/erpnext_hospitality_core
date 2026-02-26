import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    columns = [
        {"label": _("Payment Ref"), "fieldname": "name", "fieldtype": "Link", "options": "Payment Entry", "width": 140},
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Mode"), "fieldname": "mode_of_payment", "fieldtype": "Data", "width": 120},
        {"label": _("Party"), "fieldname": "party_name", "fieldtype": "Data", "width": 150},
        {"label": _("Folio Ref"), "fieldname": "reference_no", "fieldtype": "Data", "width": 150},
        {"label": _("Amount"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Type"), "fieldname": "payment_type", "fieldtype": "Data", "width": 80}
    ]

    # Filters
    date_from = filters.get("from_date")
    date_to = filters.get("to_date")
    reception = filters.get("hotel_reception")

    # SQL Logic:
    # 1. Payment Entry must be Submitted (docstatus=1)
    # 2. Match Date Range
    # 3. Match Reference No to Guest Folio naming conventions (FOLIO-xxxxx or MASTER-xxxxx)
    #    OR checks if the reference_no actually exists in the Guest Folio table for robustness.
    
    conditions = ""
    if reception:
        conditions += " AND pe.hotel_reception = %(hotel_reception)s"

    sql = f"""
        SELECT
            pe.name,
            pe.posting_date,
            pe.mode_of_payment,
            pe.party_name,
            pe.reference_no,
            pe.paid_amount,
            pe.payment_type
        FROM
            `tabPayment Entry` pe
        WHERE
            pe.docstatus = 1
            AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s
            {conditions}
            AND (
                pe.reference_no LIKE 'FOLIO%%' 
                OR pe.reference_no LIKE 'MASTER%%' 
                OR pe.remarks LIKE '%%Hotel%%'
                OR EXISTS (SELECT 1 FROM `tabGuest Folio` gf WHERE gf.name = pe.reference_no)
            )
        ORDER BY
            pe.mode_of_payment, pe.posting_date
    """

    data = frappe.db.sql(sql, filters, as_dict=True)

    # Calculate Totals by Mode
    total_cash = sum(d.paid_amount for d in data if d.mode_of_payment == 'Cash')
    total_card = sum(d.paid_amount for d in data if d.mode_of_payment != 'Cash')
    
    if data:
        data.append({"party_name": "<b>TOTAL CASH</b>", "paid_amount": total_cash})
        data.append({"party_name": "<b>TOTAL OTHER</b>", "paid_amount": total_card})

    return columns, data