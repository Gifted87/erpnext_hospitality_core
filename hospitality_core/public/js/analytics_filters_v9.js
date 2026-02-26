/**
 * Hospitality Analytics Dashboard - v9 (WORD FOR WORD MONOLITHIC REBUILD)
 * 
 * "the filetering logic must not be seperated from the chart logic. 
 * the data used to draw the chart must colme from the filter. 
 * the date is set, the syste,m retrives the data from the data base 
 * and the chart displayus that data. when the date is changed, 
 * the data is refetched and t6he chart used the new dsata in real time."
 */

frappe.provide('frappe.hospitality');

frappe.hospitality.AnalyticsEngineV9 = class {
    constructor() {
        this.fromDate = frappe.datetime.add_days(frappe.datetime.now_date(), -30);
        this.toDate = frappe.datetime.now_date();
        this.charts = {};
        this.chartNames = [
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
        this.setup_observer();
        this.init();
    }

    init() {
        if (!this.is_correct_page()) return;
        console.log('[v9] Core Engine Initializing...');
        this.inject_controls();
        this.refresh_all();
    }

    is_correct_page() {
        return window.location.href.includes('hospitality-analytics') ||
            window.location.href.includes('hospitality_analytics') ||
            (frappe.container.page && frappe.container.page.page && frappe.container.page.page.name.includes('hospitality_analytics'));
    }

    setup_observer() {
        // Self-healing: if the workspace re-renders, re-inject controls
        const observer = new MutationObserver((mutations) => {
            if (this.is_correct_page() && !$('#hos-analytics-panel-v9').children().length) {
                console.log('[v9] Workspace change detected, re-injecting...');
                this.inject_controls();
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    inject_controls() {
        const $target = $('#hos-analytics-panel-v9');
        if (!$target.length) return;

        $target.empty().html(`
            <div style="background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%); padding: 25px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);">
                <div class="row">
                    <div class="col-sm-5">
                        <label style="color: #a0aec0; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; display: block;">From Date</label>
                        <input type="date" id="v9-from-date" class="form-control" value="${this.fromDate}" style="background: #ffffff; border: none; border-radius: 8px; font-weight: 600;">
                    </div>
                    <div class="col-sm-5">
                        <label style="color: #a0aec0; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; display: block;">To Date</label>
                        <input type="date" id="v9-to-date" class="form-control" value="${this.toDate}" style="background: #ffffff; border: none; border-radius: 8px; font-weight: 600;">
                    </div>
                    <div class="col-sm-2" style="display: flex; align-items: flex-end;">
                        <button id="v9-refresh-btn" class="btn btn-primary btn-block" style="border-radius: 8px; font-weight: 700;">UPDATE</button>
                    </div>
                </div>
            </div>
        `);

        // REAL TIME: Listen for input changes
        $('#v9-from-date, #v9-to-date').on('change', (e) => {
            this.fromDate = $('#v9-from-date').val();
            this.toDate = $('#v9-to-date').val();
            console.log(`[v9] Real-time change detected: ${this.fromDate} to ${this.toDate}`);
            this.refresh_all();
        });

        $('#v9-refresh-btn').on('click', () => this.refresh_all());
    }

    refresh_all() {
        if (!this.fromDate || !this.toDate) return;
        frappe.show_alert({ message: __('Refetching Data...'), indicator: 'blue' });
        this.chartNames.forEach(name => this.process_chart(name));
    }

    process_chart(chartName) {
        // 1. Target the destination
        let $container = $(`[data-widget-name="${chartName}"], [chart_name="${chartName}"]`).find('.widget-body, .chart-container').first();
        if (!$container.length) $container = $(`div[data-chart-name="${chartName}"]`).find('.chart-container');
        if (!$container.length) {
            $(`.widget-title:contains("${chartName}")`).closest('.widget').find('.widget-body').each(function () {
                $container = $(this);
            });
        }

        if (!$container.length) return;

        // 2. Clone and Replace to kill legacy observers
        const oldNode = $container[0];
        const newNode = oldNode.cloneNode(false);
        oldNode.parentNode.replaceChild(newNode, oldNode);
        $(newNode).html('<div style="padding: 40px; text-align: center; color: #718096;">Fetching Database...</div>');

        // 3. Fetch Data and Draw Chart (Inseparable Logic)
        frappe.call({
            method: 'hospitality_core.hospitality_core.dashboard_data.get_hospitality_analytics_data',
            args: {
                chart_name: chartName,
                from_date: this.fromDate,
                to_date: this.toDate
            },
            callback: (r) => {
                const data = r.message;
                newNode.innerHTML = '';
                if (!data) {
                    newNode.innerHTML = '<div style="padding: 40px; text-align: center; color: #a0aec0;">No Data Found</div>';
                    return;
                }

                // Render logic
                let type = 'line';
                if (chartName.includes('Distribution') || chartName.includes('Breakdown') || chartName.includes('Mode')) {
                    type = chartName.includes('Guest') ? 'pie' : 'donut';
                } else if (chartName.includes('Reception')) {
                    type = 'bar';
                }

                new frappe.Chart(newNode, {
                    title: chartName,
                    data: data,
                    type: type,
                    height: 250,
                    colors: ['#667eea', '#764ba2', '#ecc94b', '#48bb78', '#f56565'],
                    axisOptions: { xIsSeries: true, shortenYAxisNumbers: 1 }
                });
            }
        });
    }
};

// Launch the monolithic engine
$(document).on('page-change', () => {
    setTimeout(() => {
        window.hos_analytics_v9 = new frappe.hospitality.AnalyticsEngineV9();
    }, 800);
});

if (document.readyState === 'complete') {
    window.hos_analytics_v9 = new frappe.hospitality.AnalyticsEngineV9();
}
