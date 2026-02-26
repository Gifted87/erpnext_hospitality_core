import frappe

def run():
    print("--- Final Migration Verification ---")
    date_from = '2026-01-16'
    date_to = '2026-01-20'
    
    # Mimic Daily Sales Consumption Report SQL
    sql = """
        SELECT 
            ft.posting_date, ft.item, ft.amount, ft.parent, ft.description
        FROM `tabFolio Transaction` ft
        INNER JOIN `tabGuest Folio` gf ON ft.parent = gf.name
        WHERE ft.posting_date BETWEEN %s AND %s
        AND ft.amount > 0
        AND ft.description LIKE 'Historical Revenue %%'
    """
    data = frappe.db.sql(sql, (date_from, date_to), as_dict=True)
    
    print(f"Total Revenue Records found in Folio Transactions (Linked to Folios): {len(data)}")
    for row in data:
        print(f"  Date: {row.posting_date}, Amount: {row.amount}, Folio: {row.parent}")

    # Check GL Entries for Sales Account
    sales_acct = "Room Bookings - EHH"
    gls = frappe.get_all('GL Entry', 
        filters={'posting_date': ['between', [date_from, date_to]], 'account': sales_acct, 'credit': ['>', 0]},
        fields=['posting_date', 'credit', 'voucher_no'])
    
    # Group by date for easier comparison
    daily_stats = {}
    for g in gls:
        d = str(g.posting_date)
        daily_stats[d] = daily_stats.get(d, 0) + g.credit
    
    print(f"\nGL Revenue Stats (by date):")
    for d in sorted(daily_stats.keys()):
        print(f"  {d}: {daily_stats[d]}")
