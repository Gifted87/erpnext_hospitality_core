import frappe

def run():
    print("--- Detailed GL Entry & Transaction Check ---")
    
    # Check Jan 16
    date = "2026-01-16"
    print(f"\nChecking financials for {date}:")
    
    # Check Folios
    folios = frappe.get_all('Guest Folio', 
        filters={'close_date': date, 'status': 'Closed'}, 
        fields=['name', 'status'])
    print(f"Closed Folios for {date}: {len(folios)}")
    for f in folios:
        txns = frappe.get_all('Folio Transaction', filters={'parent': f.name}, fields=['item', 'amount', 'docstatus', 'name'])
        print(f"  Folio: {f.name}, Transactions: {len(txns)}")
        for t in txns:
            print(f"    - {t.name}: {t.item} ({t.amount}) status:{t.docstatus}")

    # Check GL Entries
    gls = frappe.get_all('GL Entry', 
        filters={'posting_date': date}, 
        fields=['name', 'account', 'debit', 'credit', 'voucher_no', 'voucher_type', 'remarks'])
    print(f"GL Entries for {date}: {len(gls)}")
    for g in gls:
        print(f"  - {g.account}: Dr {g.debit} Cr {g.credit} | Voucher: {g.voucher_type} {g.voucher_no} | Remarks: {g.remarks[:50]}")

    # Check for Room Rent specific entries
    sales_acct = frappe.db.get_value("POS Profile", {"name": "Main Profile"}, "income_account") or "Room Bookings - EHH"
    print(f"\nExpected Income Account: {sales_acct}")
    
    room_sales = frappe.get_all('GL Entry', 
        filters={'posting_date': ['between', ['2026-01-16', '2026-01-20']], 'account': sales_acct},
        fields=['posting_date', 'credit'])
    print(f"Room Sales entries found: {len(room_sales)}")
    for s in room_sales:
        print(f"  Date: {s.posting_date}, Credit: {s.credit}")
