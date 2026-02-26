frappe.query_reports["End of Day Report"] = {
    "filters": [
        {
            "fieldname": "date",
            "label": __("Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
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
