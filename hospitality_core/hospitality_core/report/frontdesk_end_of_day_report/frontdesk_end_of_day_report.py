# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{
			"fieldname": "metric",
			"label": _("Metric"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "value",
			"label": _("Value"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "description",
			"label": _("Description"),
			"fieldtype": "Data",
			"width": 300
		}
	]

def get_data(filters):
	if not filters or not filters.get("date"):
		return []

	report_date = filters.get("date")
	reception = filters.get("hotel_reception")  # Can be None for all receptions

	data = []

	# 1. New Check-ins
	check_in_filters = {
		"arrival_date": report_date,
		"status": ["in", ["Checked In", "Checked Out"]]
	}
	if reception:
		check_in_filters["hotel_reception"] = reception
	check_ins = frappe.db.count("Hotel Reservation", check_in_filters)
	
	# Refine Check-in query: Actually status could be 'Checked In' or 'Checked Out' if they left same day, 
	# but primarily we want to know how many ARRIVED this day.
	# Let's trust 'arrival_date' and status != Cancelled/Reserved?
	# "Reserved" implies they haven't arrived yet (no show or future).
	# So status in Checked In, Checked Out.
	
	data.append({
		"metric": "New Check-ins",
		"value": check_ins,
		"description": "Number of guests who arrived and checked in on this date."
	})

	# 2. Retained (Stay-overs)
	# Guests who arrived BEFORE today and depart AFTER today.
	if reception:
		retained = frappe.db.sql("""
			SELECT count(name) FROM `tabHotel Reservation`
			WHERE
				arrival_date < %s
				AND departure_date > %s
				AND hotel_reception = %s
				AND status IN ('Checked In', 'Checked Out')
		""", (report_date, report_date, reception))[0][0]
	else:
		retained = frappe.db.sql("""
			SELECT count(name) FROM `tabHotel Reservation`
			WHERE
				arrival_date < %s
				AND departure_date > %s
				AND status IN ('Checked In', 'Checked Out')
		""", (report_date, report_date))[0][0]

	data.append({
		"metric": "Retained Guests",
		"value": retained,
		"description": "Guests currently in-house (arrived before today, leaving after today)."
	})

	# 3. Departures (Check-outs)
	departure_filters = {
		"departure_date": report_date,
		"status": "Checked Out"
	}
	if reception:
		departure_filters["hotel_reception"] = reception
	top_departures = frappe.db.count("Hotel Reservation", departure_filters)

	data.append({
		"metric": "Departures",
		"value": top_departures,
		"description": "Number of guests who checked out on this date."
	})

	# 4. Sales Consumption
	# Sum of Folio Transactions posted on this date, linked to guests in this reception.
	if reception:
		sales_consumption = frappe.db.sql("""
			SELECT SUM(ft.amount)
			FROM `tabFolio Transaction` ft
			JOIN `tabGuest Folio` gf ON ft.parent = gf.name
			WHERE
				ft.posting_date = %s
				AND gf.hotel_reception = %s
				AND ft.is_void = 0
				AND gf.docstatus < 2
				AND (ft.reference_doctype != 'Payment Entry' OR ft.reference_doctype IS NULL)
		""", (report_date, reception))[0][0] or 0.0
	else:
		sales_consumption = frappe.db.sql("""
			SELECT SUM(ft.amount)
			FROM `tabFolio Transaction` ft
			JOIN `tabGuest Folio` gf ON ft.parent = gf.name
			WHERE
				ft.posting_date = %s
				AND ft.is_void = 0
				AND gf.docstatus < 2
				AND (ft.reference_doctype != 'Payment Entry' OR ft.reference_doctype IS NULL)
		""", (report_date,))[0][0] or 0.0

	data.append({
		"metric": "Sales Consumption (Gross)",
		"value": frappe.format_value(sales_consumption, currency=frappe.get_cached_value('Company',  frappe.defaults.get_user_default("Company"),  "default_currency")),
		"description": "Total value of services/goods consumed (Inclusive of Taxes)."
	})

	# Breakdown for Sales Consumption
	from hospitality_core.hospitality_core.api.accounting import get_tax_breakdown
	sales_taxes = get_tax_breakdown(sales_consumption)
	company_currency = frappe.get_cached_value('Company', frappe.defaults.get_user_default("Company"), "default_currency")

	data.append({
		"metric": "  - Net Sales",
		"value": frappe.format_value(sales_taxes["net_amount"], currency=company_currency),
		"description": "Base revenue before taxes."
	})
	data.append({
		"metric": "  - Consumption Tax (5%)",
		"value": frappe.format_value(sales_taxes["ct_amount"], currency=company_currency),
		"description": "5% Consumption Tax deduction."
	})
	data.append({
		"metric": "  - VAT (7.5%)",
		"value": frappe.format_value(sales_taxes["vat_amount"], currency=company_currency),
		"description": "7.5% VAT deduction."
	})
	data.append({
		"metric": "  - Service Charge (10%)",
		"value": frappe.format_value(sales_taxes["sc_amount"], currency=company_currency),
		"description": "10% Service Charge deduction."
	})

	# 5. Payment
	# Sum of Payment Entries for this reception on this date.
	if reception:
		payments = frappe.db.sql("""
			SELECT SUM(paid_amount)
			FROM `tabPayment Entry`
			WHERE
				posting_date = %s
				AND hotel_reception = %s
				AND docstatus = 1
		""", (report_date, reception))[0][0] or 0.0
	else:
		payments = frappe.db.sql("""
			SELECT SUM(paid_amount)
			FROM `tabPayment Entry`
			WHERE
				posting_date = %s
				AND docstatus = 1
		""", (report_date,))[0][0] or 0.0

	data.append({
		"metric": "Total Payments",
		"value": frappe.format_value(payments, currency=frappe.get_cached_value('Company',  frappe.defaults.get_user_default("Company"),  "default_currency")),
		"description": "Total payments collected at this reception."
	})

	# 6. Analytics
	# Occupancy = (Retained + New Check-ins) / Total Rooms in Reception
	room_filters = {
		"is_enabled": 1,
		"status": ["!=", "Out of Order"]
	}
	if reception:
		room_filters["hotel_reception"] = reception
	total_rooms = frappe.db.count("Hotel Room", room_filters)

	occupancy_pct = 0.0
	if total_rooms > 0:
		# Occupied = Retained + Check-ins (Assuming check-ins stayed the night, which is typical for EOD report)
		occupied_rooms = retained + check_ins
		occupancy_pct = (occupied_rooms / total_rooms) * 100.0

	data.append({
		"metric": "Occupancy",
		"value": f"{occupancy_pct:.2f}%",
		"description": f"Occupancy Percentage ({retained + check_ins} occupied / {total_rooms} available rooms)."
	})

	# 7. Expenses
	if reception:
		expenses_by_cat = frappe.db.sql("""
			SELECT expense_category, SUM(grand_total) as amount
			FROM `tabHospitality Expense`
			WHERE
				expense_date = %s
				AND hotel_reception = %s
				AND docstatus = 1
			GROUP BY expense_category
		""", (report_date, reception), as_dict=1)
	else:
		expenses_by_cat = frappe.db.sql("""
			SELECT expense_category, SUM(grand_total) as amount
			FROM `tabHospitality Expense`
			WHERE
				expense_date = %s
				AND docstatus = 1
			GROUP BY expense_category
		""", (report_date,), as_dict=1)

	total_expenses = sum(e.amount for e in expenses_by_cat)
	company_currency = frappe.get_cached_value('Company', frappe.defaults.get_user_default("Company"), "default_currency")

	data.append({
		"metric": "Total Expenses",
		"value": frappe.format_value(total_expenses, currency=company_currency),
		"description": "Total expenses logged for this date (including taxes)."
	})

	for exp in expenses_by_cat:
		data.append({
			"metric": f"  - {exp.expense_category}",
			"value": frappe.format_value(exp.amount, currency=company_currency),
			"description": f"Expenses for category {exp.expense_category}"
		})

	# 8. Net Profit/Loss
	net_pl = sales_taxes["net_amount"] - total_expenses
	data.append({
		"metric": "Net Profit/Loss",
		"value": frappe.format_value(net_pl, currency=company_currency),
		"description": "Total Net Sales minus Total Expenses."
	})
	
	return data
