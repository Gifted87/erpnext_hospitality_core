import json

file_path = '/home/erpnext/frappe-bench/apps/hospitality_core/hospitality_core/hospitality_core/workspace/hospitality/hospitality.json'

with open(file_path, 'r') as f:
    data = json.load(f)

changed = False

def update_links(links):
    global changed
    for link in links:
        # If it's a report and we want it to be a query report link
        if link.get('link_type') == 'Report' and link.get('is_query_report') == 1:
            # Remove report_ref_doctype if it exists
            if 'report_ref_doctype' in link:
                del link['report_ref_doctype']
                changed = True

# Update links in 'links' array
update_links(data.get('links', []))

if changed:
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=1)
    print("Successfully removed report_ref_doctype from query reports.")
else:
    print("No changes needed (keys might already be gone).")
