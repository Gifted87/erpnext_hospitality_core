frappe.dashboards.chart_sources["Hospitality Analytics"] = {
    method: "hospitality_core.hospitality_core.dashboard_data.get_hospitality_analytics_data",
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_days(frappe.datetime.nowdate(), -30)
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.nowdate()
        }
    ]
};
