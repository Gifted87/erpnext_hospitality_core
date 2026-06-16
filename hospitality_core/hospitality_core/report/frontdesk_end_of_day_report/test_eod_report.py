from hospitality_core.hospitality_core.report.end_of_day_report.end_of_day_report import execute
from frappe.utils import nowdate

print("Running End of Day Report Test...")
try:
    # Use dummy filters
    filters = {
        "date": nowdate(),
        "hotel_reception": "Test Reception" # This might need to be a real ID to return data, but empty is fine for error checking
    }
    
    # We might need a real reception ID if the query strictly checks FK constraints or if we want to see data.
    # Let's try to fetch one first if possible, or just catch the error if it fails due to missing ID
    import frappe
    if frappe.db.exists("Hotel Reception"):
        filters["hotel_reception"] = frappe.db.get_value("Hotel Reception", {}, "name")
        print(f"Using Reception: {filters['hotel_reception']}")
    
    columns, data = execute(filters)
    print("Columns:", len(columns))
    print("Data Rows:", len(data))
    for row in data:
        print(row)
        
    print("Test Complete: Success")
except Exception as e:
    print(f"Test Failed: {e}")
    import traceback
    traceback.print_exc()
