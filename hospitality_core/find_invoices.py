import frappe

def execute():
    # Find all Paid POS Invoices with pos_profile containing "bush bar" (case-insensitive)
    invoices = frappe.get_all(
        "POS Invoice",
        filters={
            "docstatus": 1,
            "status": "Paid",
            "pos_profile": ["like", "%bush bar%"]
        },
        fields=["name", "pos_profile", "status", "grand_total"]
    )
    
    print(f"Found {len(invoices)} invoices to cancel.")
    for inv in invoices:
        print(f"- {inv.name}: {inv.pos_profile} | {inv.status} | {inv.grand_total}")
