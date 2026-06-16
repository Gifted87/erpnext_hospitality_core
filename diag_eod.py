import frappe

def check_eod_data():
    frappe.init(site="185.170.58.232")
    frappe.connect()
    
    # Check if POS Closing Entries exist for the date
    entries = frappe.get_all("POS Closing Entry", filters={"posting_date": "2026-03-12", "docstatus": 1})
    print(f"Submitted POS Closing Entries: {entries}")
    
    # Check if the child Doctype exists
    print(f"EOD Closing Entry exists: {frappe.db.exists('DocType', 'EOD Closing Entry')}")
    
    # Check the latest report
    latest_report = frappe.get_all("End of Day Sales Generator", order_by="creation desc", limit=1)
    if latest_report:
        doc = frappe.get_doc("End of Day Sales Generator", latest_report[0].name)
        print(f"Latest Report: {doc.name}")
        print(f"Net Sales: {doc.net_sales}")
        print(f"Child Entries Count: {len(doc.get('associated_closing_entries') or [])}")
        for row in doc.get('associated_closing_entries') or []:
            print(f" - {row.pos_closing_entry}")

if __name__ == "__main__":
    check_eod_data()
