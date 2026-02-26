/**
 * Hospitality Analytics Date Filters - v8.1 (CLONE & REPLACE + AUTO-REFRESH)
 * This version uses a destructive "Clone & Replace" strategy to ensure 
 * no legacy observers or listeners cause the "removeChild" error.
 */

frappe.provide('frappe.hospitality');

frappe.hospitality.AnalyticsDashboardV8 = class {
    constructor() {
        this.page = null;
        this.fromDate = null;
        this.toDate = null;
        console.log('[v8.1] Constructor called');
        this.init();
    }

    init() {
        const url = window.location.href;
        const page_name = frappe.container?.page?.page?.name || "";

        const isAnalyticsPage = url.includes('hospitality-analytics') ||
            url.includes('hospitality_analytics') ||
            page_name.includes('hospitality_analytics');

        console.log('[v8.1] Page detection:', { url, page_name, isAnalyticsPage });

        if (!isAnalyticsPage) {
            // Check if we are on a workspace that looks like ours
            if (!$('.widget-chart').length && !$('.ce-block').length) return;
        }

        if (!frappe.container.page || !frappe.container.page.page) {
            console.log('[v8.1] Page not ready, retrying...');
            setTimeout(() => this.init(), 500);
            return;
        }

        this.page = frappe.container.page.page;
        console.log('[v8.1] Initializing on Page:', this.page.name);

        this.setup_filters();
    }

    setup_filters() {
        // Prevent duplicate fields
        $(this.page.wrapper).find('.frappe-control[data-fieldname="hos_date_range_v8"]').remove();

        console.log('[v8.1] Adding date range field');
        this.date_field = this.page.add_field({
            label: __('Date Range'),
            fieldtype: 'DateRange',
            fieldname: 'hos_date_range_v8',
            default: [
                frappe.datetime.add_days(frappe.datetime.now_date(), -30),
                frappe.datetime.now_date()
            ],
            change: () => {
                const val = this.date_field.get_value();
                console.log('[v8.1] Date changed:', val);
                if (val && val.length === 2) {
                    this.fromDate = val[0];
                    this.toDate = val[1];
                    // AUTO REFRESH on change
                    this.update_dashboard();
                }
            }
        });

        this.page.set_primary_action(__('Update Analytics'), () => {
            console.log('[v8.1] Primary action clicked');
            this.update_dashboard();
        }, 'refresh');

        const initialVal = this.date_field.get_value();
        if (initialVal) {
            this.fromDate = initialVal[0];
            this.toDate = initialVal[1];
        }
    }

    update_dashboard() {
        if (!this.fromDate || !this.toDate) {
            console.warn('[v8.1] Missing dates for update');
            return;
        }

        frappe.show_alert({ message: __('Updating Analytics...'), indicator: 'blue' });
        console.log('[v8.1] Updating dashboard with dates:', this.fromDate, this.toDate);

        const chartNames = [
            "Occupancy Rate Trend",
            "Average Daily Rate (ADR)",
            "RevPAR Trend",
            "Guest Type Distribution",
            "Revenue vs Expense Trend",
            "Gross Profit Margin Trend",
            "Expense Breakdown",
            "Sales by Reception",
            "Payment Mode Distribution",
            "Maintenance Cost by Room Type"
        ];

        let foundCount = 0;
        chartNames.forEach(name => {
            if (this.refresh_chart(name)) foundCount++;
        });

        console.log(`[v8.1] Attempted refresh on ${chartNames.length} names, found ${foundCount} containers.`);
    }

    refresh_chart(chartName) {
        // Find the container
        let $container = $(`[data-widget-name="${chartName}"], [chart_name="${chartName}"]`).find('.widget-body, .chart-container').first();
        if (!$container.length) $container = $(`div[data-chart-name="${chartName}"]`).find('.chart-container');

        // Final fallback: look for any element that has the name as text if attributes fail
        if (!$container.length) {
            $(`.widget-title:contains("${chartName}")`).closest('.widget').find('.widget-body').each(function () {
                $container = $(this);
            });
        }

        if (!$container.length) return false;

        console.log('[v8.1] Refreshing chart container for:', chartName);

        // CLONE & REPLACE Strategy
        const oldNode = $container[0];
        if (!oldNode || !oldNode.parentNode) return false;

        const newNode = oldNode.cloneNode(false);
        oldNode.parentNode.replaceChild(newNode, oldNode);

        const $newNode = $(newNode);
        $newNode.html('<div class="text-muted p-4 text-center">Loading...</div>');

        frappe.call({
            method: 'hospitality_core.hospitality_core.dashboard_data.get_hospitality_analytics_data',
            args: {
                chart_name: chartName,
                from_date: this.fromDate,
                to_date: this.toDate
            },
            callback: (r) => {
                if (r.message) {
                    this.render_chart(newNode, chartName, r.message);
                } else {
                    $newNode.html('<div class="text-muted p-4 text-center">No Data</div>');
                }
            }
        });
        return true;
    }

    render_chart(element, title, data) {
        let type = 'line';
        if (title.includes('Distribution') || title.includes('Breakdown') || title.includes('Mode')) {
            type = title.includes('Guest') ? 'pie' : 'donut';
        } else if (title.includes('Reception')) {
            type = 'bar';
        }

        element.innerHTML = '';

        try {
            new frappe.Chart(element, {
                title: title,
                data: data,
                type: type,
                height: 250,
                colors: ['#667eea', '#764ba2', '#f6ad55', '#4fd1c5', '#f687b3'],
                axisOptions: {
                    xIsSeries: true,
                    shortenYAxisNumbers: 1
                }
            });
        } catch (e) {
            console.error('[v8.1] Error rendering chart', title, e);
            element.innerHTML = '<div class="text-danger p-4 text-center">Rendering Error</div>';
        }
    }
};

// Global init control
window.setup_hospitality_analytics_v8 = function () {
    console.log('[v8.1] Global setup trigger');
    window.hospitality_analytics_v8 = new frappe.hospitality.AnalyticsDashboardV8();
};

$(document).on('page-change', function () {
    console.log('[v8.1] Page change event');
    setTimeout(window.setup_hospitality_analytics_v8, 800);
});

if (document.readyState === 'complete') {
    window.setup_hospitality_analytics_v8();
}
