import json

file_path = '/home/erpnext/frappe-bench/apps/hospitality_core/hospitality_core/hospitality_core/workspace/hospitality/hospitality.json'

with open(file_path, 'r') as f:
    data = json.load(f)

changed = False

def update_links(links):
    global changed
    for link in links:
        if link.get('link_type') == 'Report' and link.get('is_query_report') == 0:
            link['is_query_report'] = 1
            changed = True

# Update links in 'links' array
update_links(data.get('links', []))

# Update links in 'shortcuts' array (if any behave like reports, but normally they are URL/DocType/Page)
# The shortcuts in this file seem to be URL, Page, or DocType, so skipping.

# Update 'content' which is a stringified JSON
if 'content' in data:
    try:
        content_data = json.loads(data['content'])
        content_changed = False
        # Content structure is list of blocks. Some blocks are charts/cards, not links directly in the same format.
        # But wait, the json provided shows 'links' as a separate top-level list. The 'content' is for the dashboard blocks.
        # The sidebar links are defined in the 'links' list.
        # The user complaint "the way you linked the reports in the hospitality workspace" likely refers to the sidebar links.
        # Let's double check if 'content' has report links.
        # Content has "type": "shortcut", "type": "card", "type": "header".
        # The detailed links are in "links".
        pass
    except Exception as e:
        print(f"Error parsing content: {e}")

if changed:
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=1)
    print("Successfully updated is_query_report to 1 for all reports.")
else:
    print("No changes needed.")
