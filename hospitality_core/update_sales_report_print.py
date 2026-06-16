import frappe

def execute():
    print_format_name = "Sales Report"
    
    # Delete the old one if it exists with the old name
    if frappe.db.exists("Print Format", "End of Day Sales Receipt"):
        frappe.delete_doc("Print Format", "End of Day Sales Receipt", force=1)
        print("Deleted old print format: End of Day Sales Receipt")

    html_content = """
    <style>
        .report-header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #333; padding-bottom: 10px; }
        .report-title { font-size: 24px; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
        .report-info { font-size: 14px; color: #555; }
        
        .section-header { 
            background-color: #f8f9fa; 
            padding: 8px 12px; 
            font-weight: bold; 
            border-left: 4px solid #333; 
            margin: 20px 0 10px 0;
            text-transform: uppercase;
            font-size: 16px;
        }
        
        .kpi-container { display: flex; flex-wrap: wrap; margin-bottom: 20px; }
        .kpi-box { 
            flex: 1; 
            min-width: 200px; 
            padding: 15px; 
            border: 1px solid #eee; 
            margin: 5px; 
            border-radius: 4px;
            background-color: #fff;
        }
        .kpi-label { font-size: 12px; color: #777; text-transform: uppercase; margin-bottom: 5px; }
        .kpi-value { font-size: 18px; font-weight: bold; color: #222; }
        
        .report-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px; }
        .report-table th { 
            background-color: #eee; 
            padding: 10px; 
            text-align: left; 
            border-bottom: 2px solid #ddd;
            font-weight: bold;
        }
        .report-table td { padding: 8px 10px; border-bottom: 1px solid #eee; }
        .text-right { text-align: right !important; }
        .text-bold { font-weight: bold; }
        .text-danger { color: #d9534f; }
        .text-success { color: #5cb85c; }
        
        @media print {
            .page-break { page-break-before: always; }
            body { padding: 20px; }
        }
    </style>

    <div class="report-header">
        <div class="report-title">Sales Report</div>
        <div class="report-info">
            <strong>{{ doc.company }}</strong><br>
            Departments: {% if doc.pos_profiles %}{{ doc.pos_profiles|map(attribute='pos_profile')|join(', ') }}{% else %}All POS Profiles{% endif %}<br>
            Period: {{ doc.get_formatted("from_date_time") }} to {{ doc.get_formatted("to_date_time") }}<br>
            Generated on: {{ frappe.utils.format_datetime(frappe.utils.now_datetime(), "dd-mm-yyyy HH:mm:ss") }}
        </div>
    </div>

    <div class="section-header">Financial Summary</div>
    <div class="kpi-container">
        <div class="kpi-box">
            <div class="kpi-label">Expected Amount</div>
            <div class="kpi-value">{{ doc.get_formatted("total_expected_amount") }}</div>
        </div>
        <div class="kpi-box">
            <div class="kpi-label">Actual Amount</div>
            <div class="kpi-value">{{ doc.get_formatted("total_actual_amount") }}</div>
        </div>
        <div class="kpi-box">
            <div class="kpi-label">Difference</div>
            <div class="kpi-value {% if doc.total_difference < 0 %}text-danger{% elif doc.total_difference > 0 %}text-success{% endif %}">
                {{ doc.get_formatted("total_difference") }}
            </div>
        </div>
    </div>

    <div class="kpi-container">
        <div class="kpi-box">
            <div class="kpi-label">Net Sales</div>
            <div class="kpi-value">{{ doc.get_formatted("net_sales") }}</div>
        </div>
        <div class="kpi-box">
            <div class="kpi-label">VAT (7.5%)</div>
            <div class="kpi-value">{{ doc.get_formatted("vat_amount") }}</div>
        </div>
        <div class="kpi-box">
            <div class="kpi-label">Service Charge (10%)</div>
            <div class="kpi-value">{{ doc.get_formatted("service_charge") }}</div>
        </div>
        <div class="kpi-box">
            <div class="kpi-label">Consumption Tax (5%)</div>
            <div class="kpi-value">{{ doc.get_formatted("consumption_tax") }}</div>
        </div>
    </div>

    <div class="kpi-container">
        <div class="kpi-box">
            <div class="kpi-label">Total Transactions</div>
            <div class="kpi-value">{{ doc.total_transactions }}</div>
        </div>
        <div class="kpi-box" style="flex: 3;">
            <div class="kpi-label">Cashier(s)</div>
            <div class="kpi-value" style="font-size: 14px;">{{ doc.cashiers or "N/A" }}</div>
        </div>
    </div>

    <div class="section-header">Item Sales Breakdown</div>
    <table class="report-table">
        <thead>
            <tr>
                <th>POS Profile</th>
                <th>Item Code</th>
                <th>Item Name</th>
                <th class="text-right">Qty</th>
                <th class="text-right">Amount</th>
            </tr>
        </thead>
        <tbody>
            {% for row in doc.eod_item_sales %}
            <tr>
                <td>{{ row.pos_profile }}</td>
                <td>{{ row.item_code }}</td>
                <td>{{ row.item_name }}</td>
                <td class="text-right">{{ row.qty_sold }}</td>
                <td class="text-right">{{ row.get_formatted("amount") }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="section-header">Item Group Summary</div>
    <table class="report-table" style="width: 50%;">
        <thead>
            <tr>
                <th>Item Group</th>
                <th class="text-right">Qty</th>
                <th class="text-right">Amount</th>
            </tr>
        </thead>
        <tbody>
            {% for row in doc.eod_item_group_sales %}
            <tr>
                <td>{{ row.item_group }}</td>
                <td class="text-right">{{ row.qty_sold }}</td>
                <td class="text-right">{{ row.get_formatted("amount") }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="section-header">Payment Mode Summary</div>
    <table class="report-table">
        <thead>
            <tr>
                <th>Payment Mode</th>
                <th class="text-right">Expected</th>
                <th class="text-right">Actual</th>
                <th class="text-right">Difference</th>
            </tr>
        </thead>
        <tbody>
            {% for row in doc.eod_payment_summary %}
            <tr>
                <td class="text-bold">{{ row.payment_mode }}</td>
                <td class="text-right">{{ row.get_formatted("expected_amount") }}</td>
                <td class="text-right">{{ row.get_formatted("actual_amount") }}</td>
                <td class="text-right {% if row.difference < 0 %}text-danger{% endif %}">{{ row.get_formatted("difference") }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    {% if doc.eod_discrepancies|length > 0 %}
    <div class="section-header text-danger">Associated Closing Entries & Discrepancies</div>
    <table class="report-table">
        <thead>
            <tr>
                <th>POS Closing Entry</th>
                <th>POS Profile</th>
                <th class="text-right">Difference</th>
            </tr>
        </thead>
        <tbody>
            {% for row in doc.eod_discrepancies %}
            <tr>
                <td>{{ row.pos_closing_entry }}</td>
                <td>{{ row.pos_profile }}</td>
                <td class="text-right {% if row.difference < 0 %}text-danger{% endif %}">{{ row.get_formatted("difference") }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}

    {% if doc.eod_stock_balance|length > 0 %}
    <div class="page-break"></div>
    <div class="section-header">Closing Stock Balances</div>
    <table class="report-table">
        <thead>
            <tr>
                <th>POS Profile</th>
                <th>Warehouse</th>
                <th>Item Code</th>
                <th>Item Name</th>
                <th class="text-right">Balance Qty</th>
                <th>UOM</th>
            </tr>
        </thead>
        <tbody>
            {% for row in doc.eod_stock_balance %}
            <tr>
                <td>{{ row.pos_profile }}</td>
                <td>{{ row.warehouse }}</td>
                <td>{{ row.item_code }}</td>
                <td>{{ row.item_name }}</td>
                <td class="text-right">{{ row.balance_qty }}</td>
                <td>{{ row.uom }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}

    <div style="margin-top: 50px; display: flex; justify-content: space-between;">
        <div style="border-top: 1px solid #333; width: 200px; text-align: center; padding-top: 5px;">
            Prepared By
        </div>
        <div style="border-top: 1px solid #333; width: 200px; text-align: center; padding-top: 5px;">
            Authorized Signature
        </div>
    </div>
    """

    if not frappe.db.exists("Print Format", print_format_name):
        doc = frappe.get_doc({
            "doctype": "Print Format",
            "name": print_format_name,
            "doc_type": "Sales Report",
            "module": "Hospitality Core",
            "custom_format": 1,
            "print_format_type": "Jinja",
            "html": html_content,
            "standard": "No"
        })
        doc.insert(ignore_permissions=True)
        print(f"Created Print Format: {print_format_name}")
    else:
        doc = frappe.get_doc("Print Format", print_format_name)
        doc.html = html_content
        doc.save(ignore_permissions=True)
        print(f"Updated Print Format: {print_format_name}")
    
    # Set as default for Sales Report
    frappe.db.set_value("DocType", "Sales Report", "default_print_format", print_format_name)
    
    frappe.db.commit()

if __name__ == "__main__":
    execute()
