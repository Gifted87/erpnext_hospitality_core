frappe.query_reports["Hospitality Expense Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company") || "Edo Heritage Hotel",
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
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
            "fieldname": "expense_category",
            "label": __("Expense Category"),
            "fieldtype": "Link",
            "options": "Expense Category"
        },
        {
            "fieldname": "supplier",
            "label": __("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier"
        },
        {
            "fieldname": "hotel_reception",
            "label": __("Hotel Reception"),
            "fieldtype": "Link",
            "options": "Hotel Reception"
        },
        {
            "fieldname": "workflow_state",
            "label": __("Approval State"),
            "fieldtype": "Link",
            "options": "Workflow State"
        }
    ]
};
