import json

filepath = "/home/erpnext/frappe-bench/apps/hospitality_core/hospitality_core/hospitality_core/doctype/end_of_day_sales_generator/end_of_day_sales_generator.json"
with open(filepath, 'r') as f:
    data = json.load(f)

new_fields = [
    {
        "fieldname": "vat_amount",
        "fieldtype": "Currency",
        "label": "VAT (7.5%)",
        "read_only": 1
    },
    {
        "fieldname": "service_charge",
        "fieldtype": "Currency",
        "label": "Service Charge (10%)",
        "read_only": 1
    },
    {
        "fieldname": "consumption_tax",
        "fieldtype": "Currency",
        "label": "Consumption Tax (5%)",
        "read_only": 1
    }
]

idx = next((i for i, f in enumerate(data['fields']) if f.get('fieldname') == 'net_sales'), None)
if idx is not None:
    data['fields'] = [f for f in data['fields'] if f.get('fieldname') not in ('vat_amount', 'service_charge', 'consumption_tax')]
    idx = next(i for i, f in enumerate(data['fields']) if f.get('fieldname') == 'net_sales')
    for nf in reversed(new_fields):
        data['fields'].insert(idx, nf)

    data['field_order'] = [f for f in data['field_order'] if f not in ('vat_amount', 'service_charge', 'consumption_tax')]
    fo_idx = data['field_order'].index('net_sales')
    for nf in reversed(new_fields):
        data['field_order'].insert(fo_idx, nf['fieldname'])

with open(filepath, 'w') as f:
    json.dump(data, f, indent=1)
print("Updated json")
