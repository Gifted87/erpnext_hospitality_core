frappe.query_reports["Room Only Sales"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "hotel_reception",
			"label": __("Hotel Reception"),
			"fieldtype": "Link",
			"options": "Hotel Reception"
		}
	],
	"onload": function(report) {
		report.page.add_inner_button(__("Print Room Only Sales"), function() {
			let from_date = report.get_filter_value("from_date");
			let to_date = report.get_filter_value("to_date");
			if (!from_date || !to_date) {
				frappe.msgprint(__("Please select From Date and To Date first."));
				return;
			}
			let hotel_reception = report.get_filter_value("hotel_reception") || "";
			let url = frappe.urllib.get_full_url(
				`/api/method/hospitality_core.hospitality_core.report.room_only_sales.room_only_sales.print_room_only_sales` +
				`?from_date=${encodeURIComponent(from_date)}&to_date=${encodeURIComponent(to_date)}&hotel_reception=${encodeURIComponent(hotel_reception)}`
			);
			window.open(url, "_blank");
		}, __("Actions"));
	}
};

