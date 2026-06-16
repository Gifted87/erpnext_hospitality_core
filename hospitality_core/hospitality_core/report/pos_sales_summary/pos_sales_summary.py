import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate


# ─── POS profile to exclude from the Summary section only ─────────────────────
BREAKFAST_POS_PROFILE = "Breakfast"


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 320},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 160},
	]

	if not filters.get("date"):
		return columns, []

	closing_entries = get_closing_entries(filters)
	payment_map = get_payment_map([e.name for e in closing_entries]) if closing_entries else {}

	profile_totals = get_profile_totals(closing_entries, payment_map)

	data = []
	no_profile_filter = not filters.get("pos_profile")

	# ── Per-profile rows (ALL profiles shown here, including Breakfast) ────────
	for pos_profile, totals in profile_totals.items():
		data.append({"description": "<b>{}</b>".format(pos_profile), "amount": None})
		data.append({"description": _("Total Sales"), "amount": totals["sales"]})

		for mode, amount in sorted(totals["payments"].items()):
			if flt(amount):
				data.append({"description": mode, "amount": amount})

		data.append({"description": _("Total Collected"), "amount": totals["collected"]})
		data.append({"description": "", "amount": None})

	# ── Summary Section ────────────────────────────────────────────────────────
	# When no profile filter is active: exclude the Breakfast POS profile from
	# the summary totals and payment breakdown.
	data.append({"description": _("<b>Summary</b>"), "amount": None})
	data.extend(build_summary_section(filters, profile_totals, no_profile_filter))

	return columns, data


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_profile_totals(closing_entries, payment_map):
	profile_totals = {}
	for entry in closing_entries:
		profile = profile_totals.setdefault(
			entry.pos_profile,
			{"sales": 0, "collected": 0, "payments": {}},
		)
		profile["sales"] += flt(entry.grand_total)
		for mode, amount in payment_map.get(entry.name, {}).items():
			profile["payments"][mode] = profile["payments"].get(mode, 0) + amount
			profile["collected"] += amount
	return profile_totals


def build_summary_section(filters, profile_totals, no_profile_filter):
	data = []
	if no_profile_filter:
		# Build summary totals excluding the Breakfast POS profile
		summary_sales = 0
		summary_collected = 0
		summary_payments = {}

		for pos_profile, totals in profile_totals.items():
			if pos_profile in [BREAKFAST_POS_PROFILE, "Reception", "Reception (New)"]:
				continue  # excluded from summary only
			summary_sales += totals["sales"]
			summary_collected += totals["collected"]
			for mode, amount in totals["payments"].items():
				summary_payments[mode] = summary_payments.get(mode, 0) + amount

		# Add Accommodation row FIRST in the summary
		accom_data = get_accommodation_data(filters.get("date"))
		accom_total = accom_data["total"]
		accom_payments = accom_data["payments"]

		data.append({"description": _("Accommodation"), "amount": accom_total})

		# Accommodation payment breakdown (from daily payment collection)
		accom_collected = 0
		for mode, amount in sorted(accom_payments.items()):
			if flt(amount):
				data.append({"description": "  {}".format(mode), "amount": amount})
				accom_collected += amount
				
		data.append({"description": _("Total Payments Collected"), "amount": accom_collected})

		data.append({"description": "", "amount": None})

		# Non-Breakfast POS totals
		data.append({"description": _("Total POS Sales"), "amount": summary_sales})

		for mode, amount in sorted(summary_payments.items()):
			if flt(amount):
				data.append({"description": mode, "amount": amount})

		combined_total = accom_total + summary_sales
		data.append({"description": _("<b>Total Sales</b>"), "amount": combined_total})

	else:
		# Standard view when a specific profile is selected — no Breakfast exclusion needed
		summary_sales = sum(t["sales"] for t in profile_totals.values())
		summary_collected = sum(t["collected"] for t in profile_totals.values())
		summary_payments = {}
		for totals in profile_totals.values():
			for mode, amount in totals["payments"].items():
				summary_payments[mode] = summary_payments.get(mode, 0) + amount

		data.append({"description": _("Total Sales"), "amount": summary_sales})

		for mode, amount in sorted(summary_payments.items()):
			if flt(amount):
				data.append({"description": mode, "amount": amount})
				
	return data

def get_closing_entries(filters):
	closing_date = add_days(getdate(filters.get("date")), 1)
	conditions = ["docstatus = 1", "posting_date = %(closing_date)s"]
	params = {"closing_date": closing_date}

	if filters.get("pos_profile"):
		conditions.append("pos_profile = %(pos_profile)s")
		params["pos_profile"] = filters.get("pos_profile")

	return frappe.db.sql(
		"SELECT name, pos_profile, grand_total FROM `tabPOS Closing Entry` WHERE {} ORDER BY pos_profile, name".format(
			' AND '.join(conditions)
		),
		params,
		as_dict=True,
	)


def get_payment_map(closing_entry_names):
	if not closing_entry_names:
		return {}

	rows = frappe.db.sql(
		"""
		SELECT parent, mode_of_payment, SUM(expected_amount - opening_amount) AS amount
		FROM `tabPOS Closing Entry Detail`
		WHERE parent IN %(closing_entry_names)s
		GROUP BY parent, mode_of_payment
		""",
		{"closing_entry_names": tuple(closing_entry_names)},
		as_dict=True,
	)

	payment_map = {}
	for row in rows:
		amount = flt(row.amount)
		if not amount:
			continue
		payment_map.setdefault(row.parent, {})[row.mode_of_payment] = amount

	return payment_map


def get_accommodation_data(date):
	"""
	Returns total room-only sales and payments for the given date
	by calling the exact logic from the source reports to ensure 100% consistency.
	"""
	from hospitality_core.hospitality_core.report.room_only_sales.room_only_sales import get_data as get_room_sales_data
	from hospitality_core.hospitality_core.report.daily_payment_collection.daily_payment_collection import execute as get_daily_payments

	# 1. Room Sales
	sales_rows = get_room_sales_data({"from_date": date, "to_date": date})
	# The last row is the total row if there are records
	total = sales_rows[-1]["amount"] if sales_rows else 0

	# 2. Payments
	_, payment_data = get_daily_payments({"from_date": date, "to_date": date})
	payments = {}
	for row in payment_data:
		if row.get("voucher_type"):  # Ignore the appended TOTAL rows
			mode = row.get("mode_of_payment")
			if mode:
				payments[mode] = payments.get(mode, 0) + flt(row.get("paid_amount"))

	return {"total": total, "payments": payments}
