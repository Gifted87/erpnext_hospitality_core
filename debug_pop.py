import frappe
from frappe.utils import flt

def debug_eod():
    frappe.init(site="185.170.58.232")
    frappe.connect()
    
    # Get the latest report to test with
    latest_report = frappe.get_all("End of Day Sales Generator", order_by="creation desc", limit=1)
    if not latest_report:
        print("No report found")
        return
        
    doc = frappe.get_doc("End of Day Sales Generator", latest_report[0].name)
    print(f"Report: {doc.name}")
    print(f"Company: {doc.company}, Date: {doc.from_date_time}")
    
    closing_entries = doc.get_closing_entries()
    print(f"Found {len(closing_entries)} closing entries.")
    
    if closing_entries:
        closing_entry_names = tuple([e.name for e in closing_entries])
        differences = frappe.db.sql("""
            SELECT parent, SUM(difference) as diff
            FROM `tabPOS Closing Entry Detail`
            WHERE parent IN %s
            GROUP BY parent
        """, (closing_entry_names,), as_dict=True)
        
        diff_map = {d.parent: d.diff for d in differences}
        print(f"Diff Map: {diff_map}")
        
        print("Appending to eod_discrepancies (simulation)...")
        appended_data = []
        for entry in closing_entries:
            row_data = {
                "pos_closing_entry": entry.name,
                "pos_profile": entry.pos_profile,
                "difference": diff_map.get(entry.name, 0.0)
            }
            appended_data.append(row_data)
            print(f"Row: {row_data}")
            
        print(f"Current rows in DB doc: {len(doc.get('eod_discrepancies'))}")
        
        # Test actual execution
        try:
            doc.clear_existing_data()
            doc.flag_discrepancies(closing_entries)
            print(f"Rows after flag_discrepancies called: {len(doc.get('eod_discrepancies'))}")
        except Exception as e:
            print(f"Error calling flag_discrepancies: {str(e)}")

if __name__ == "__main__":
    debug_eod()
