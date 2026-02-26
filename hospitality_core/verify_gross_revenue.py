def verify_gross_revenue_report():
    from hospitality_core.hospitality_core.report.gross_revenue_report.gross_revenue_report import execute as run_report
    print("--- Starting Gross Revenue Report Verification ---")
    
    # We use the data created during the historical migration (Jan 1-15, 2026)
    # or the data from the wholesome expense verification (current date).
    
    # 1. Test for a specific date range covering historical data
    filters = {
        "company": "Edo Heritage Hotel",
        "from_date": "2026-01-01",
        "to_date": "2026-01-15",
        "group_by": "Room Type"
    }
    
    columns, data = run_report(filters)
    
    print(f"\nReport Results (Grouped by {filters['group_by']}) for {filters['from_date']} to {filters['to_date']}:")
    if not data:
        print("No data found for this period.")
    else:
        for row in data:
            print(f"Room Type: {row.get('room_type')} | Qty: {row.get('qty')} | Rev: {row.get('revenue')} | Exp: {row.get('expenses')} | GP: {row.get('gross_profit')} ({row.get('gross_profit_pct'):.2f}%)")

    # 2. Test Grouping by Room
    filters["group_by"] = "Room"
    columns, data = run_report(filters)
    print(f"\nReport Results (Grouped by {filters['group_by']}):")
    for row in data[:5]: # Show first 5
        print(f"Room: {row.get('room_number')} | Rev: {row.get('revenue')} | Exp: {row.get('expenses')} | GP: {row.get('gross_profit')}")

    # 3. Test Grouping by Reception
    filters["group_by"] = "Reception"
    columns, data = run_report(filters)
    print(f"\nReport Results (Grouped by {filters['group_by']}):")
    for row in data:
        print(f"Reception: {row.get('hotel_reception')} | Rev: {row.get('revenue')} | Exp: {row.get('expenses')} | GP: {row.get('gross_profit')}")

    # 4. Test for Today (should include test expenses)
    today = frappe.utils.nowdate()
    # Group by Reception to see ALL expenses (direct + indirect)
    filters = {
        "company": "Edo Heritage Hotel",
        "from_date": today,
        "to_date": today,
        "group_by": "Reception"
    }
    columns, data = run_report(filters)
    print(f"\nReport Results (Current Date: {today}, Grouped by Reception):")
    if not data:
        print("No data found for today.")
    else:
        for row in data:
            print(f"Reception: {row.get('hotel_reception')} | Rev: {row.get('revenue')} | Exp: {row.get('expenses')} | GP: {row.get('gross_profit')}")

    # Group by Room Type to see if direct expenses show up
    filters["group_by"] = "Room Type"
    columns, data = run_report(filters)
    print(f"\nReport Results (Current Date: {today}, Grouped by Room Type):")
    for row in data:
        print(f"Room Type: {row.get('room_type')} | Rev: {row.get('revenue')} | Exp: {row.get('expenses')} | GP: {row.get('gross_profit')}")

    print("\n--- Verification Complete ---")

verify_gross_revenue_report()
