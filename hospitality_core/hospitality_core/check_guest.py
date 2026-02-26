import frappe

def check():
    guest = frappe.db.get_value('Guest', {'full_name': 'Historical Migration Sync'}, ['name', 'customer'], as_dict=True)
    if guest:
        print(f"Guest: {guest.name}, Customer: {guest.customer}")
        if not guest.customer:
            print("WARNING: No Customer linked!")
    else:
        print("Guest 'Historical Migration Sync' not found.")

if __name__ == "__main__":
    check()
