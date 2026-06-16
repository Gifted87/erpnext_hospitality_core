frappe.query_reports["Daily Payment Collection"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.now_date(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.now_date(),
            "reqd": 1
        },
        {
            "fieldname": "hotel_reception",
            "label": __("Hotel Reception"),
            "fieldtype": "Link",
            "options": "Hotel Reception",
            "reqd": 0
        },
        {
            "fieldname": "poster",
            "label": __("Poster"),
            "fieldtype": "Link",
            "options": "User",
            "reqd": 0
        },
        {
            "fieldname": "mode_of_payment",
            "label": __("Mode of Payment"),
            "fieldtype": "Link",
            "options": "Mode of Payment",
            "reqd": 0
        }
    ],
    "onload": function(report) {
        report.page.add_inner_button(__("Print Payment Collection"), function() {
            let from_date = report.get_filter_value("from_date");
            let to_date = report.get_filter_value("to_date");
            if (!from_date || !to_date) {
                frappe.msgprint(__("Please select From Date and To Date first."));
                return;
            }
            let hotel_reception = report.get_filter_value("hotel_reception") || "";
            let poster = report.get_filter_value("poster") || "";
            let mode_of_payment = report.get_filter_value("mode_of_payment") || "";
            let url = frappe.urllib.get_full_url(
                `/api/method/hospitality_core.hospitality_core.report.daily_payment_collection.daily_payment_collection.print_daily_payment_collection` +
                `?from_date=${encodeURIComponent(from_date)}&to_date=${encodeURIComponent(to_date)}` +
                `&hotel_reception=${encodeURIComponent(hotel_reception)}&poster=${encodeURIComponent(poster)}` +
                `&mode_of_payment=${encodeURIComponent(mode_of_payment)}`
            );
            window.open(url, "_blank");
        }, __("Actions"));
    }
};