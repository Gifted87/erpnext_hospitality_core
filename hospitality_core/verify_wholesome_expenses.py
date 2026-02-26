import frappe
from frappe.utils import nowdate, flt

def verify_wholesome_expenses():
    print("--- Starting Wholesome Expense Verification ---")
    
    # 1. Ensure Categories exist (from hierarchy)
    category = "Electrical"
    if not frappe.db.exists("Expense Category", category):
        print(f"FAILURE: Category {category} not found. Run setup_categories.py first.")
        return

    # 2. Mock a Maintenance Request
    m_req = frappe.new_doc("Hotel Maintenance Request")
    m_req.room = frappe.get_all("Hotel Room", limit=1)[0].name
    m_req.issue_type = "Electrical"
    m_req.description = "Flickering lights in room"
    m_req.status = "Reported"
    m_req.reported_by = "Administrator"
    m_req.insert()
    print(f"Created Maintenance Request: {m_req.name}")

    # 3. Create Expense with TAX
    expense = frappe.new_doc("Hospitality Expense")
    expense.expense_date = frappe.utils.nowdate()
    expense.expense_category = category
    expense.amount = 10000
    expense.paid_via = "Cash"
    expense.maintenance_request = m_req.name
    expense.description = "Replaced 5 LED bulbs and starter"
    
    # Add VAT
    expense.append("taxes", {
        "account_head": "VAT - EHH",
        "description": "7.5% VAT",
        "rate": 7.5
    })
    
    expense.insert()
    print(f"Created Expense: {expense.name} (Draft)")
    print(f"Net Amount: {expense.amount} | Tax: {expense.total_taxes} | Grand Total: {expense.grand_total}")

    # 4. Apply Workflow Action: Submit for Approval -> Approve
    from frappe.model.workflow import apply_workflow
    
    # First transition: Draft -> Pending Approval
    apply_workflow(expense, "Submit for Approval")
    print("Expense transitioned to Pending Approval")
    
    # Second transition: Pending Approval -> Approved (Submits)
    apply_workflow(expense, "Approve")
    print(f"Expense Submitted (Approved): {expense.name}")

    # 5. Verify GL Entries (Multi-line)
    gl_entries = frappe.get_all("GL Entry", 
        filters={"voucher_no": expense.name},
        fields=["account", "debit", "credit"],
        order_by="debit desc"
    )
    
    print("\nWholesome GL Entries:")
    for entry in gl_entries:
        print(f"Account: {entry.account} | Dr: {entry.debit} | Cr: {entry.credit}")

    # Expectations: 
    # Dr Expense 10000
    # Dr VAT 750
    # Cr Cash 10750
    if len(gl_entries) == 3:
        print("\nSUCCESS: 3 GL Entries found (Expense, Tax, Payment).")
    else:
        print(f"\nFAILURE: Expected 3 GL Entries, found {len(gl_entries)}.")

    # 6. Verify Maintenance Cost Roll-up
    m_req.reload()
    print(f"\nMaintenance Request Total Cost: {m_req.total_expenses}")
    if frappe.utils.flt(m_req.total_expenses) == frappe.utils.flt(expense.grand_total):
        print("SUCCESS: Maintenance cost rolled up correctly.")
    else:
        print(f"FAILURE: Maintenance cost mismatch. Expected {expense.grand_total}, got {m_req.total_expenses}")

    # 7. Verify End of Day Report
    from hospitality_core.hospitality_core.report.end_of_day_report.end_of_day_report import execute
    filters = {"date": frappe.utils.nowdate()}
    columns, result = execute(filters)
    
    print("\nEnd of Day Report (Granular breakdown):")
    for row in result:
        if "Total Expenses" in row['metric'] or "Net Profit/Loss" in row['metric'] or "Electrical" in row['metric']:
            print(f"{row['metric']}: {row['value']}")

    frappe.db.commit()
    print("--- Wholesome Verification Complete (Data Committed) ---")

if __name__ == "__main__":
    verify_wholesome_expenses()
