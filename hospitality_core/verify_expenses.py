import frappe
from frappe import _
from frappe.utils import nowdate, flt

def verify_expenses():
    print("--- Starting Expense Verification ---")
    
    # 1. Setup Expense Category
    category_name = "Maintenance"
    if not frappe.db.exists("Expense Category", category_name):
        cat = frappe.new_doc("Expense Category")
        cat.category_name = category_name
        cat.default_expense_account = "Administrative Expenses - EHH"
        cat.insert()
        frappe.db.commit()
        print(f"Created Expense Category: {category_name}")
    else:
        print(f"Expense Category {category_name} already exists.")

    # 2. Mock a Maintenance Request
    m_req = frappe.new_doc("Hotel Maintenance Request")
    m_req.room = frappe.get_all("Hotel Room", limit=1)[0].name
    m_req.issue_type = "Plumbing"
    m_req.description = "Leaking pipe in bathroom"
    m_req.status = "Reported"
    m_req.reported_by = "Administrator"
    m_req.insert()
    print(f"Created Maintenance Request: {m_req.name}")

    # 3. Create Expense linked to Maintenance
    expense = frappe.new_doc("Hospitality Expense")
    expense.expense_date = frappe.utils.nowdate()
    expense.expense_category = category_name
    expense.amount = 5000
    expense.paid_via = "Cash"
    # payment_account and expense_account should be auto-set on validate
    expense.maintenance_request = m_req.name
    expense.description = "Bought new PVC pipes and adhesive"
    expense.insert()
    
    print(f"Created Expense: {expense.name}")
    print(f"Expense Account: {expense.expense_account}")
    print(f"Payment Account: {expense.payment_account}")
    
    # 4. Submit Expense
    expense.submit()
    print(f"Submitted Expense: {expense.name}")

    # 5. Verify GL Entries
    gl_entries = frappe.get_all("GL Entry", 
        filters={"voucher_no": expense.name},
        fields=["account", "debit", "credit"]
    )
    
    print("\nGL Entries for Expense:")
    for entry in gl_entries:
        print(f"Account: {entry.account} | Dr: {entry.debit} | Cr: {entry.credit}")

    if len(gl_entries) == 2:
        print("\nSUCCESS: 2 GL Entries found.")
    else:
        print(f"\nFAILURE: Expected 2 GL Entries, found {len(gl_entries)}.")

    # 6. Verify End of Day Report Integration
    from hospitality_core.hospitality_core.report.end_of_day_report.end_of_day_report import execute
    filters = {"date": frappe.utils.nowdate()}
    columns, result = execute(filters)
    
    print("\nEnd of Day Report (P/L section):")
    for row in result:
        if row['metric'] in ["Total Expenses", "Net Profit/Loss"]:
            print(f"{row['metric']}: {row['value']}")

    print("--- Verification Complete ---")

if __name__ == "__main__":
    verify_expenses()
