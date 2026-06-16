import frappe

def execute():
    if not frappe.db.exists("Print Format", "End of Day Sales Receipt"):
        doc = frappe.get_doc({
            "doctype": "Print Format",
            "name": "End of Day Sales Receipt",
            "doc_type": "End of Day Sales Generator",
            "module": "Hospitality Core",
            "custom_format": 1,
            "print_format_type": "Jinja",
            "html": """
            <style>
                .eod-header { text-align: center; margin-bottom: 20px; }
                .eod-kpi { display: flex; justify-content: space-between; font-weight: bold; border-bottom: 1px solid #ccc; padding-bottom: 10px; margin-bottom: 20px;}
                .eod-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
                .eod-table th, .eod-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                .eod-table th { background-color: #f2f2f2; }
                .text-right { text-align: right !important; }
                .text-danger { color: red; }
            </style>
            <div class="eod-header">
                <h2>End of Day Sales Report</h2>
                <p>Company: {{ doc.company }}</p>
                <p>Period: {{ doc.from_date_time }} to {{ doc.to_date_time }}</p>
                <p>Status: {{ doc.pos_entry_status }}</p>
            </div>
            
            <div class="eod-kpi">
                <div>
                    <span>Total Expected:</span><br>
                    <span>{{ doc.get_formatted("total_expected_amount") }}</span>
                </div>
                <div>
                    <span>Total Actual:</span><br>
                    <span>{{ doc.get_formatted("total_actual_amount") }}</span>
                </div>
                <div>
                    <span>Difference:</span><br>
                    <span class="{% if doc.total_difference < 0 %}text-danger{% endif %}">{{ doc.get_formatted("total_difference") }}</span>
                </div>
            </div>
            
            <div class="eod-kpi" style="border: none;">
                <div>
                    <span>Net Sales:</span><br>
                    <span>{{ doc.get_formatted("net_sales") }}</span>
                </div>
                <div>
                    <span>Total Taxes:</span><br>
                    <span>{{ doc.get_formatted("total_taxes") }}</span>
                </div>
                <div>
                    <span>Total Transactions:</span><br>
                    <span>{{ doc.total_transactions }}</span>
                </div>
            </div>
            
            <h4>Item Sales</h4>
            <table class="eod-table">
                <tr>
                    <th>Item</th>
                    <th>Qty Sold</th>
                    <th class="text-right">Amount</th>
                </tr>
                {% for row in doc.eod_item_sales %}
                <tr>
                    <td>{{ row.item_name }}</td>
                    <td>{{ row.qty_sold }}</td>
                    <td class="text-right">{{ row.get_formatted("amount") }}</td>
                </tr>
                {% endfor %}
            </table>
            
            <h4>Item Group Sales</h4>
            <table class="eod-table">
                <tr>
                    <th>Item Group</th>
                    <th>Qty Sold</th>
                    <th class="text-right">Amount</th>
                </tr>
                {% for row in doc.eod_item_group_sales %}
                <tr>
                    <td>{{ row.item_group }}</td>
                    <td>{{ row.qty_sold }}</td>
                    <td class="text-right">{{ row.get_formatted("amount") }}</td>
                </tr>
                {% endfor %}
            </table>
            
            <h4>Payment Summary</h4>
            <table class="eod-table">
                <tr>
                    <th>Mode</th>
                    <th class="text-right">Expected</th>
                    <th class="text-right">Actual</th>
                    <th class="text-right">Difference</th>
                </tr>
                {% for row in doc.eod_payment_summary %}
                <tr>
                    <td>{{ row.payment_mode }}</td>
                    <td class="text-right">{{ row.get_formatted("expected_amount") }}</td>
                    <td class="text-right">{{ row.get_formatted("actual_amount") }}</td>
                    <td class="text-right {% if row.difference < 0 %}text-danger{% endif %}">{{ row.get_formatted("difference") }}</td>
                </tr>
                {% endfor %}
            </table>
            
            {% if doc.eod_discrepancies|length > 0 %}
            <h4 class="text-danger">Discrepancies / Shortages</h4>
            <table class="eod-table">
                <tr>
                    <th>POS Closing Entry</th>
                    <th>POS Profile</th>
                    <th class="text-right">Difference</th>
                </tr>
                {% for row in doc.eod_discrepancies %}
                <tr>
                    <td>{{ row.pos_closing_entry }}</td>
                    <td>{{ row.pos_profile }}</td>
                    <td class="text-right text-danger">{{ row.get_formatted("difference") }}</td>
                </tr>
                {% endfor %}
            </table>
            {% endif %}
            """
        })
        doc.insert(ignore_permissions=True)
        print("Created Print Format")
    else:
        print("Print Format already exists")
        
    frappe.db.commit()
