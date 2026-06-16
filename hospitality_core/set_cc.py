import frappe

def set_default_cost_center():
    companies = frappe.get_all("Company", fields=["name", "cost_center"])
    for c in companies:
        if not c.cost_center:
            # Let's see if there's a cost center like "Main - <company abbr>"
            cc = frappe.get_all("Cost Center", filters={"company": c.name}, order_by="is_group asc", limit=1)
            if cc:
                frappe.db.set_value("Company", c.name, "cost_center", cc[0].name)
                print(f"Set Default Cost Center for {c.name} to {cc[0].name}")
            else:
                print(f"No Cost Center found for {c.name}")
        else:
            print(f"Company {c.name} already has default Cost Center: {c.cost_center}")
    frappe.db.commit()

set_default_cost_center()
