frappe.query_reports["Reservations Report"] = {
	"filters": [
		{
			"fieldname": "date",
			"label": __("Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "view_mode",
			"label": __("View Mode"),
			"fieldtype": "Select",
			"options": "Arrivals\nDepartures\nIn-House",
			"default": "Arrivals",
			"reqd": 1
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nReserved\nChecked In\nChecked Out\nCancelled"
		},
		{
			"fieldname": "hotel_reception",
			"label": __("Hotel Reception"),
			"fieldtype": "Link",
			"options": "Hotel Reception"
		},
		{
			"fieldname": "room_type",
			"label": __("Room Type"),
			"fieldtype": "Link",
			"options": "Hotel Room Type"
		}
	]
};
