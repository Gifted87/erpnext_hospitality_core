frappe.query_reports["House List"] = {
    "filters": [
        {
            "fieldname": "date",
            "label": __("Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        }
    ],
    "onload": function(report) {
        report.page.add_inner_button(__("Print House List"), function() {
            let date = report.get_filter_value("date");
            if (!date) {
                frappe.msgprint(__("Please select a date first."));
                return;
            }
            
            // Build the URL to print the report using standard Frappe print view
            // The standard print view can render Jinja templates if we pass the right context
            // But since this is a report, we'll use a custom whitelisted API to fetch and render
            let url = frappe.urllib.get_full_url(
                `/api/method/hospitality_core.hospitality_core.report.house_list.house_list.print_house_list?date=${date}`
            );
            window.open(url, "_blank");
        }, __("Actions"));
    }
};