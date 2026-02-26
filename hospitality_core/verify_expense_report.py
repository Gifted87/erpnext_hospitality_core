def verify_expense_report():
    from hospitality_core.hospitality_core.report.hospitality_expense_report.hospitality_expense_report import execute as fetch_expenses
    print("--- Starting Hospitality Expense Report Verification ---")
    
    # 1. Test for Today (should include test expenses created previously)
    today = frappe.utils.nowdate()
    filters = {
        "company": "Edo Heritage Hotel",
        "from_date": today,
        "to_date": today
    }
    
    columns, data = fetch_expenses(filters)
    
    print(f"\nDetailed Expense Results for {today}:")
    if not data:
        print("No expenses found for today. Make sure verify_wholesome_expenses.py was run.")
    else:
        for row in data:
            print(f"ID: {row.get('name')} | Cat: {row.get('expense_category')} | Net: {row.get('amount')} | Tax: {row.get('total_taxes')} | Grand: {row.get('grand_total')} | State: {row.get('workflow_state')}")

    # 2. Test Category Filter
    if data:
        cat = data[0].get('expense_category')
        filters['expense_category'] = cat
        _, filtered_data = fetch_expenses(filters)
        print(f"\nFiltered by Category ({cat}): {len(filtered_data)} entries found.")

    # 3. Test Workflow State Filter
    if data:
        state = "Approved"
        filters['workflow_state'] = state
        filters.pop('expense_category', None)
        _, filtered_data = fetch_expenses(filters)
        print(f"\nFiltered by State ({state}): {len(filtered_data)} entries found.")

    print("\n--- Verification Complete ---")

verify_expense_report()
