import frappe
from hospitality_core.hospitality_core.api.accounting import make_gl_entries_for_folio_transaction, reclassify_pos_taxes
from frappe.utils import nowdate, flt

def verify():
    # 1. Setup Mock Settings
    settings = frappe.get_single("Hospitality Accounting Settings")
    settings.consumption_tax_account = "Consumption Tax - EH"
    settings.vat_account = "Value Added Tax - EH"
    settings.service_charge_account = "Service Charge - EH"
    settings.save()
    
    # Ensure accounts exist (Mock check or creation if needed, but assuming they exist since user approved)
    # For verification, we just want to see if the logic generates correct GL objects
    
    print("Verification Start...")
    
    # 2. Test Folio Transaction (Room Charge)
    # Total = 122.50 -> Net = 100, CT = 5, VAT = 7.5, SC = 10
    mock_txn = frappe._dict({
        "name": "TEST-TXN-001",
        "parent": "TEST-FOLIO-001",
        "amount": 122.50,
        "posting_date": nowdate(),
        "item": "Room Rent",
        "description": "Room Charge Test",
        "reference_doctype": None
    })
    
    # We need to mock frappe.db.get_doc or insert a real guest folio
    # Let's try to find a real one or create a dummy
    if not frappe.db.exists("Guest Folio", "TEST-FOLIO-001"):
        folio = frappe.get_doc({
            "doctype": "Guest Folio",
            "name": "TEST-FOLIO-001",
            "company": "Test Company",
            "guest": "Test Guest",
            "status": "Open"
        }).insert(ignore_permissions=True)
    
    print("\nTesting Folio Transaction Logic...")
    # Intercept gl_entries insert for verification
    # Actually, let's just run it and check GL entries
    make_gl_entries_for_folio_transaction(mock_txn)
    
    gl_entries = frappe.get_all("GL Entry", filters={"voucher_no": "TEST-FOLIO-001"}, fields=["account", "debit", "credit", "remarks"])
    for entry in gl_entries:
        print(f"Account: {entry.account}, Debit: {entry.debit}, Credit: {entry.credit}, Remarks: {entry.remarks}")

    # 3. Test POS Invoice Reclassification
    print("\nTesting POS Invoice Reclassification Logic...")
    mock_pos = frappe._dict({
        "name": "TEST-POS-001",
        "grand_total": 122.50,
        "posting_date": nowdate()
    })
    
    reclassify_pos_taxes(mock_pos)
    
    gl_entries_pos = frappe.get_all("GL Entry", filters={"voucher_no": "TEST-POS-001"}, fields=["account", "debit", "credit", "remarks"])
    for entry in gl_entries_pos:
        print(f"Account: {entry.account}, Debit: {entry.debit}, Credit: {entry.credit}, Remarks: {entry.remarks}")

    print("\nVerification Complete.")

if __name__ == "__main__":
    verify()
