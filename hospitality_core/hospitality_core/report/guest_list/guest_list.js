frappe.query_reports["Guest List"] = {
	"filters": [
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
	],
	"onload": function(report) {
		report.page.add_inner_button(__("Print Guest List"), function() {
			let hotel_reception = report.get_filter_value("hotel_reception") || "";
			let room_type = report.get_filter_value("room_type") || "";
			let url = frappe.urllib.get_full_url(
				`/api/method/hospitality_core.hospitality_core.report.guest_list.guest_list.print_guest_list` +
				`?hotel_reception=${encodeURIComponent(hotel_reception)}&room_type=${encodeURIComponent(room_type)}`
			);
			window.open(url, "_blank");
		}, __("Actions"));
	}
};
