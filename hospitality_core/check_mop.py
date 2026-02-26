
import frappe

def check_mop():
    mop = frappe.db.get_value("Mode of Payment", "Room Charge", ["name", "type"], as_dict=True)
    print(f"Mode of Payment: {mop}")
    
    accounts = frappe.get_all("Mode of Payment Account", filters={"parent": "Room Charge"}, fields=["company", "default_account"])
    for acc in accounts:
        print(f"Company: {acc.company}, Account: {acc.default_account}")
        if acc.default_account:
            a = frappe.get_doc("Account", acc.default_account)
            print(f"  Balance Must Be: {a.balance_must_be}")

check_mop()
