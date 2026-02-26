import frappe

def initialize():
    print("--- Initializing Accounting Settings ---")
    company = "Edo Heritage Hotel"
    abbr = "EHH"
    unearned_acc = f"Unearned Revenue - {abbr}"
    
    # 1. Ensure Account Exists
    if not frappe.db.exists("Account", unearned_acc):
        print(f"Creating Account: {unearned_acc}")
        acc = frappe.new_doc("Account")
        acc.account_name = "Unearned Revenue"
        acc.parent_account = f"Current Liabilities - {abbr}"
        acc.company = company
        acc.account_type = "Liability"
        acc.balance_must_be = "Credit"
        acc.report_type = "Balance Sheet"
        acc.root_type = "Liability"
        acc.insert()
        print("Account created.")
    else:
        print(f"Account {unearned_acc} already exists.")

    # 2. Update Settings
    settings = frappe.get_doc("Hospitality Accounting Settings")
    settings.receivable_account = f"Debtors - {abbr}"
    settings.income_suspense_account = unearned_acc
    settings.income_account = f"Room Bookings - {abbr}"
    settings.cost_center = f"Main - {abbr}"
    settings.save()
    frappe.db.commit()
    print("Settings saved and committed.")

if __name__ == "__main__":
    initialize()
