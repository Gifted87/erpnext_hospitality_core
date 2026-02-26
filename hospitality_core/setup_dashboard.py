import frappe

def setup_dashboard_items():
	print("--- Setting up Dashboard Charts & Number Cards ---")
	
	# 1. Number Cards (Key Metrics)
	cards = [
		{
			"name": "Today's Occupancy %",
			"label": "Today's Occupancy %",
			"function": "Average",
			"is_standard": 1,
			"module": "Hospitality Core",
			"type": "Custom",
			"method": "hospitality_core.hospitality_core.dashboard_data.get_today_occupancy"
		},
		{
			"name": "Today's Revenue",
			"label": "Today's Revenue",
			"function": "Sum",
			"is_standard": 1,
			"module": "Hospitality Core",
			"type": "Custom",
			"method": "hospitality_core.hospitality_core.dashboard_data.get_today_revenue"
		},
		{
			"name": "Today's Expenses",
			"label": "Today's Expenses",
			"function": "Sum",
			"is_standard": 1,
			"module": "Hospitality Core",
			"type": "Custom",
			"method": "hospitality_core.hospitality_core.dashboard_data.get_today_expenses"
		}
	]
	
	for card in cards:
		if not frappe.db.exists("Number Card", card["name"]):
			doc = frappe.get_doc({"doctype": "Number Card", **card})
			doc.insert(ignore_permissions=True)
			print(f"Created Number Card: {card['name']}")

	# 2. Dashboard Chart Source
	source_name = "Hospitality Analytics"
	if not frappe.db.exists("Dashboard Chart Source", source_name):
		doc = frappe.get_doc({
			"doctype": "Dashboard Chart Source",
			"source_name": source_name,
			"module": "Hospitality Core",
			"timeseries": 1,
			"source_path": "hospitality_core.hospitality_core.dashboard_data.get_hospitality_analytics_data"
		})
		doc.insert(ignore_permissions=True)
		print(f"Created Dashboard Chart Source: {source_name}")

	# 3. Dashboard Charts
	charts = [
		{
			"chart_name": "Occupancy Rate Trend",
			"chart_type": "Custom",
			"source": source_name,
			"type": "Line",
			"color": "#3498db"
		},
		{
			"chart_name": "Average Daily Rate (ADR)",
			"chart_type": "Custom",
			"source": source_name,
			"type": "Line",
			"color": "#2ecc71"
		},
		{
			"chart_name": "RevPAR Trend",
			"chart_type": "Custom",
			"source": source_name,
			"type": "Line",
			"color": "#e67e22"
		},
		{
			"chart_name": "Guest Type Distribution",
			"chart_type": "Custom",
			"source": source_name,
			"type": "Pie",
			"color": "#1abc9c"
		},
		{
			"chart_name": "Revenue vs Expense Trend",
			"chart_type": "Custom",
			"source": source_name,
			"type": "Line",
			"color": "#34495e"
		},
		{
			"chart_name": "Expense Breakdown",
			"chart_type": "Custom",
			"source": source_name,
			"type": "Donut",
			"color": "#f1c40f"
		},
		{
			"chart_name": "Gross Profit Margin Trend",
			"chart_type": "Custom",
			"source": source_name,
			"type": "Line",
			"color": "#9b59b6"
		},
		{
			"chart_name": "Sales by Reception",
			"chart_type": "Custom",
			"source": source_name,
			"type": "Bar",
			"color": "#d35400"
		},
		{
			"chart_name": "Payment Mode Distribution",
			"chart_type": "Custom",
			"source": source_name,
			"type": "Pie",
			"color": "#7f8c8d"
		},
		{
			"chart_name": "Maintenance Cost by Room Type",
			"chart_type": "Custom",
			"source": source_name,
			"type": "Bar",
			"color": "#e74c3c"
		}
	]
	
	for chart in charts:
		chart_values = {
			"doctype": "Dashboard Chart",
			"is_standard": 1,
			"module": "Hospitality Core",
			"filters_json": "{}",
			**chart
		}
		
		if frappe.db.exists("Dashboard Chart", chart["chart_name"]):
			doc = frappe.get_doc("Dashboard Chart", chart["chart_name"])
			doc.update(chart_values)
			doc.save(ignore_permissions=True)
			print(f"Updated Dashboard Chart: {chart['chart_name']}")
		else:
			doc = frappe.get_doc(chart_values)
			doc.insert(ignore_permissions=True)
			print(f"Created Dashboard Chart: {chart['chart_name']}")
			
	frappe.db.commit()
	print("--- Setup Complete ---")

if __name__ == "__main__":
	setup_dashboard_items()
