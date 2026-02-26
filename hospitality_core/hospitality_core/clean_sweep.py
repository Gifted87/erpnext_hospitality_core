import frappe

def clean_sweep():
    print("--- TOTAL CLEAN SWEEP: Historical Migration Sync ---")
    
    guest_name = "Historical Migration Sync"
    customer_name = "Historical Migration Sync"
    
    # 1. Delete Payment Entries
    print("Deleting Payment Entries...")
    pes = frappe.get_all("Payment Entry", filters={"party": customer_name}, fields=["name", "docstatus"])
    for pe in pes:
        print(f"  Deleting PE: {pe.name}")
        if pe.docstatus == 1:
            frappe.get_doc("Payment Entry", pe.name).cancel()
        frappe.delete_doc("Payment Entry", pe.name, force=True)
        
    # 2. Delete Hotel Reservations
    print("Deleting Hotel Reservations...")
    res = frappe.get_all("Hotel Reservation", filters={"guest": guest_name})
    for r in res:
        # print(f"  Deleting Res: {r.name}")
        # Delete Linked Folio first to be safe
        folio = frappe.db.get_value("Hotel Reservation", r.name, "folio")
        if folio:
            frappe.db.sql("DELETE FROM `tabFolio Transaction` WHERE parent = %s", (folio,))
            frappe.db.sql("DELETE FROM `tabGuest Folio` WHERE name = %s", (folio,))
        frappe.delete_doc("Hotel Reservation", r.name, force=True)

    # 3. Delete any remaining Guest Folios for this guest
    print("Deleting remaining Guest Folios...")
    folios = frappe.get_all("Guest Folio", filters={"guest": guest_name})
    for f in folios:
        frappe.db.sql("DELETE FROM `tabFolio Transaction` WHERE parent = %s", (f.name,))
        frappe.db.sql("DELETE FROM `tabGuest Folio` WHERE name = %s", (f.name,))

    # 4. Delete GL Entries for the periodJan 16-21 that were created by migration
    print("Deleting GL Entries for Jan 16-21...")
    frappe.db.sql("""
        DELETE FROM `tabGL Entry` 
        WHERE posting_date BETWEEN '2026-01-16' AND '2026-01-21'
        AND (remarks LIKE 'Historical%%' OR remarks LIKE 'Ref: %%' OR remarks LIKE 'Income Realization%%')
    """)

    frappe.db.commit()
    print("--- CLEAN SWEEP COMPLETE ---")

if __name__ == "__main__":
    clean_sweep()
