import frappe

def execute():
    # 1. Delete Hotel Reservations
    reservations = frappe.get_all("Hotel Reservation", pluck="name")
    for name in reservations:
        try:
            frappe.delete_doc("Hotel Reservation", name, ignore_permissions=True, force=1)
        except frappe.DoesNotExistError:
            pass
    
    print(f"Processed {len(reservations)} Hotel Reservations.")

    # 2. Delete ALL Folio Transactions first
    frappe.db.delete("Folio Transaction")
    print("Deleted all Folio Transactions.")

    # 3. Delete Guest Folios
    folios = frappe.get_all("Guest Folio", pluck="name")
    for name in folios:
        try:
            frappe.delete_doc("Guest Folio", name, ignore_permissions=True, force=1)
        except frappe.DoesNotExistError:
            pass

    print(f"Processed {len(folios)} Guest Folios.")

    frappe.db.commit()
