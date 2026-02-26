import frappe
from hospitality_core.hospitality_core.report.end_of_day_report.end_of_day_report import execute

def verify_report():
    filters = {"date": "2026-01-05", "hotel_reception": "New Building"}
    print(f"Running report for {filters['date']}...")
    columns, data = execute(filters)
    
    for row in data:
        print(f"{row['metric']}: {row['value']}")
        
    # Validation
    retained_row = next((x for x in data if x['metric'] == "Retained Guests"), None)
    if retained_row and retained_row['value'] > 0:
        print("✔ Verification Passed: Retained Guests > 0")
    else:
        print("✘ Verification Failed: Retained Guests is 0 or missing")

# Execute directly
verify_report()
