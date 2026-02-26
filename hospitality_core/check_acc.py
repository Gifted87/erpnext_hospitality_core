
import frappe

def get_details():
    settings = frappe.get_single("Hospitality Accounting Settings")
    print(f"Income Account: {settings.income_account}")
    print(f"Suspense Account: {settings.income_suspense_account}")
    
    for acc_name in [settings.income_account, settings.income_suspense_account]:
        if acc_name:
            acc = frappe.get_doc("Account", acc_name)
            print(f"Account: {acc.name}, Balance Must Be: {acc.balance_must_be}")

get_details()
