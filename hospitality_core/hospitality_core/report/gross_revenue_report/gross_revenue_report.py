# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_columns(filters):
	group_by = filters.get("group_by")
	columns = []
	
	if group_by == "Room":
		columns.append({"label": _("Room Number (Item)"), "fieldname": "room_number", "fieldtype": "Link", "options": "Hotel Room", "width": 150})
		columns.append({"label": _("Room Type (Item Group)"), "fieldname": "room_type", "fieldtype": "Link", "options": "Hotel Room Type", "width": 150})
	elif group_by == "Room Type":
		columns.append({"label": _("Room Type (Item Group)"), "fieldname": "room_type", "fieldtype": "Link", "options": "Hotel Room Type", "width": 200})
	else: # Reception
		columns.append({"label": _("Reception (Department)"), "fieldname": "hotel_reception", "fieldtype": "Link", "options": "Hotel Reception", "width": 200})

	columns.extend([
		{"label": _("Occupied Days (Qty)"), "fieldname": "qty", "fieldtype": "Float", "width": 120},
		{"label": _("Avg Daily Rate"), "fieldname": "avg_rate", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Avg Daily Expense"), "fieldname": "avg_expense", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Gross Revenue (Inclusive)"), "fieldname": "revenue", "fieldtype": "Currency", "options": "currency", "width": 150},
		{"label": _("Net Revenue"), "fieldname": "net_revenue", "fieldtype": "Currency", "options": "currency", "width": 140},
		{"label": _("Consumption Tax (5%)"), "fieldname": "ct_amount", "fieldtype": "Currency", "options": "currency", "width": 140},
		{"label": _("VAT (7.5%)"), "fieldname": "vat_amount", "fieldtype": "Currency", "options": "currency", "width": 140},
		{"label": _("Service Charge (10%)"), "fieldname": "sc_amount", "fieldtype": "Currency", "options": "currency", "width": 140},
		{"label": _("Total Expenses (Buying Amount)"), "fieldname": "expenses", "fieldtype": "Currency", "options": "currency", "width": 150},
		{"label": _("Gross Profit (Net Rev - Exp)"), "fieldname": "gross_profit", "fieldtype": "Currency", "options": "currency", "width": 150},
		{"label": _("Gross Profit %"), "fieldname": "gross_profit_pct", "fieldtype": "Percent", "width": 120},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "hidden": 1}
	])
	
	return columns

def get_data(filters):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	reception_filter = filters.get("hotel_reception")
	group_by = filters.get("group_by")
	company = filters.get("company")
	
	currency = frappe.get_cached_value('Company', company, 'default_currency')

	# 1. Fetch Revenue Data (Charges)
	# We aggregate Folio Transactions (non-void, non-payment) linked to Reservations via Guest Folios.
	revenue_query = """
		SELECT 
			res.room as room_number,
			room.room_type,
			room.hotel_reception,
			SUM(ft.amount) as revenue,
			COUNT(DISTINCT ft.posting_date) as qty
		FROM `tabFolio Transaction` ft
		JOIN `tabGuest Folio` gf ON ft.parent = gf.name
		JOIN `tabHotel Reservation` res ON gf.reservation = res.name
		JOIN `tabHotel Room` room ON res.room = room.room_number
		WHERE 
			ft.posting_date BETWEEN %s AND %s
			AND ft.is_void = 0
			AND (ft.reference_doctype != 'Payment Entry' OR ft.reference_doctype IS NULL)
			AND gf.docstatus < 2
	"""
	
	rev_params = [from_date, to_date]
	if reception_filter:
		revenue_query += " AND room.hotel_reception = %s"
		rev_params.append(reception_filter)
		
	revenue_query += " GROUP BY res.room, room.room_type, room.hotel_reception"
	
	revenue_data = frappe.db.sql(revenue_query, tuple(rev_params), as_dict=1)

	# 2. Fetch Expense Data
	# Expenses can be linked to Receptions OR Maintenance (linked to Rooms).
	# Pro-rating logic: If linked to Maintenance, it's direct Room cost. 
	# If linked to Reception only, it's shared across all rooms in that reception.
	
	expense_query = """
		SELECT 
			maintenance_request,
			hotel_reception,
			SUM(grand_total) as expense_amount
		FROM `tabHospitality Expense`
		WHERE 
			expense_date BETWEEN %s AND %s
			AND docstatus = 1
	"""
	exp_params = [from_date, to_date]
	if reception_filter:
		expense_query += " AND hotel_reception = %s"
		exp_params.append(reception_filter)
	
	expense_query += " GROUP BY maintenance_request, hotel_reception"
	
	expense_raw = frappe.db.sql(expense_query, tuple(exp_params), as_dict=1)
	
	# Process Expenses into a mapping
	direct_expenses = {} # {room: amount}
	indirect_expenses = {} # {reception: amount}
	
	for e in expense_raw:
		if e.maintenance_request:
			room = frappe.db.get_value("Hotel Maintenance Request", e.maintenance_request, "room")
			if room:
				direct_expenses[room] = direct_expenses.get(room, 0) + flt(e.expense_amount)
		else:
			reception = e.hotel_reception
			indirect_expenses[reception] = indirect_expenses.get(reception, 0) + flt(e.expense_amount)

	# 3. Consolidate Data
	# Group by the chosen dimension
	items = {}
	
	# Helper to initialize item row
	def init_row(room_number=None, room_type=None, reception=None):
		return {
			"room_number": room_number,
			"room_type": room_type,
			"hotel_reception": reception,
			"qty": 0,
			"revenue": 0,
			"expenses": 0,
			"currency": currency
		}

	for r in revenue_data:
		key = ""
		if group_by == "Room": 
			key = r.room_number
		elif group_by == "Room Type":
			key = r.room_type
		else:
			key = r.hotel_reception or "Unknown"
			
		if key not in items:
			items[key] = init_row(r.room_number, r.room_type, r.hotel_reception)
		
		items[key]["qty"] += flt(r.qty)
		items[key]["revenue"] += flt(r.revenue)

	# Add direct expenses (Room level)
	for rm_number, e_amt in direct_expenses.items():
		rm_info = frappe.db.get_value("Hotel Room", rm_number, ["room_type", "hotel_reception"], as_dict=1)
		if not rm_info: continue
		
		key = ""
		if group_by == "Room":
			key = rm_number
		elif group_by == "Room Type":
			key = rm_info.room_type
		else: # Reception
			key = rm_info.hotel_reception or "Unknown"
			
		if key not in items:
			items[key] = init_row(rm_number, rm_info.room_type, rm_info.hotel_reception)
			
		items[key]["expenses"] += e_amt

	# Add indirect expenses (Reception level)
	for rec, e_amt in indirect_expenses.items():
		rec_key = rec or "Unknown"
		if group_by == "Reception":
			if rec_key not in items:
				items[rec_key] = init_row(reception=rec_key)
			items[rec_key]["expenses"] += e_amt
		else:
			# If grouped by Room/Room Type, we can't easily attribute indirect expenses to a single key
			# So we might want a "General" row or skip? 
			# The user wants "reception points as departments", so if we group by Room/Room type, 
			# reception-level expenses are "overhead" that isn't directly assigned to an "item".
			# However, for a Gross Revenue report, we usually only care about direct COGS (expenses linked to rooms).
			# But I'll add an "Overhead" row if there are indirect expenses not already accounted for.
			overhead_key = f"Overhead ({rec_key})"
			if overhead_key not in items:
				items[overhead_key] = init_row(reception=rec_key)
			items[overhead_key]["expenses"] += e_amt

	# 4. Final Row Calculations
	from hospitality_core.hospitality_core.api.accounting import get_tax_breakdown
	
	final_data = []
	for key, val in items.items():
		# Apply Tax Breakdown
		taxes = get_tax_breakdown(val["revenue"])
		val["net_revenue"] = taxes["net_amount"]
		val["ct_amount"] = taxes["ct_amount"]
		val["vat_amount"] = taxes["vat_amount"]
		val["sc_amount"] = taxes["sc_amount"]
		
		val["gross_profit"] = val["net_revenue"] - val["expenses"]
		val["gross_profit_pct"] = (val["gross_profit"] / val["net_revenue"] * 100.0) if val["net_revenue"] else 0
		val["avg_rate"] = (val["revenue"] / val["qty"]) if val["qty"] else 0
		val["avg_expense"] = (val["expenses"] / val["qty"]) if val["qty"] else 0
		
		if group_by == "Room":
			val["room_number"] = key
		elif group_by == "Room Type":
			val["room_type"] = key
		else:
			val["hotel_reception"] = key
			
		final_data.append(val)
		
	return final_data
