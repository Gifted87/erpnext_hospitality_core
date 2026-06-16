import json
import os

filepath = "/home/erpnext/frappe-bench/apps/hospitality_core/hospitality_core/hospitality_core/doctype/end_of_day_sales_generator/end_of_day_sales_generator.json"

with open(filepath, "r") as f:
    data = json.load(f)

# Update field_order
if "associated_closing_entries" not in data["field_order"]:
    idx = data["field_order"].index("eod_discrepancies") + 1
    data["field_order"].insert(idx, "section_break_closing_entries")
    data["field_order"].insert(idx + 1, "associated_closing_entries")

# Update fields
fieldnames = [f["fieldname"] for f in data["fields"]]
if "associated_closing_entries" not in fieldnames:
    new_fields = [
        {
            "fieldname": "section_break_closing_entries",
            "fieldtype": "Section Break",
            "label": "Associated Closing Entries"
        },
        {
            "fieldname": "associated_closing_entries",
            "fieldtype": "Table",
            "label": "Associated Closing Entries",
            "options": "EOD Closing Entry",
            "read_only": 1
        }
    ]
    # Insert before section_break_stock
    for i, field in enumerate(data["fields"]):
        if field.get("fieldname") == "section_break_stock":
            data["fields"][i:i] = new_fields
            break

with open(filepath, "w") as f:
    json.dump(data, f, indent=1)
