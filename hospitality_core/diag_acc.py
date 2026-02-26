
import frappe

def diag():
    settings = frappe.get_single("Hospitality Accounting Settings")
    print(f"--- Hospitality Accounting Settings ---")
    print(f"Income Account: {settings.income_account}")
    print(f"Income Suspense Account: {settings.income_suspense_account}")
    print(f"Receivable Account: {settings.receivable_account}")
    
    for field in ["income_account", "income_suspense_account", "receivable_account"]:
        acc_name = getattr(settings, field)
        if acc_name:
            acc = frappe.get_doc("Account", acc_name)
            print(f"Account: {acc.name}")
            print(f"  Root Type: {acc.root_type}")
            print(f"  Report Type: {acc.report_type}")
            print(f"  Account Type: {acc.account_type}")
            print(f"  Balance Must Be: {acc.balance_must_be}")
            
            # Check current balance
            balance = frappe.db.get_value("GL Entry", {"account": acc.name, "is_cancelled": 0}, "sum(debit) - sum(credit)")
            print(f"  Current Balance (Dr-Cr): {balance}")

if __name__ == "__main__":
    diag()
