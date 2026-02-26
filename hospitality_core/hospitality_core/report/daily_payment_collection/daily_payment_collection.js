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
        }
    ]
};