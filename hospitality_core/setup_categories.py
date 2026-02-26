import frappe

def create_standard_categories():
    print("Creating standard expense categories...")
    
    categories = [
        {"name": "Operations", "is_group": 1},
        {"name": "Maintenance", "is_group": 1, "parent": "Operations"},
        {"name": "Electrical", "is_group": 0, "parent": "Maintenance", "account": "Administrative Expenses - EHH"},
        {"name": "Plumbing", "is_group": 0, "parent": "Maintenance", "account": "Administrative Expenses - EHH"},
        {"name": "Utilities", "is_group": 1, "parent": "Operations"},
        {"name": "Electricity", "is_group": 0, "parent": "Utilities", "account": "Administrative Expenses - EHH"},
        {"name": "Water", "is_group": 0, "parent": "Utilities", "account": "Administrative Expenses - EHH"},
    ]

    for cat in categories:
        if not frappe.db.exists("Expense Category", cat["name"]):
            doc = frappe.new_doc("Expense Category")
            doc.category_name = cat["name"]
            doc.is_group = cat.get("is_group", 0)
            doc.parent_category = cat.get("parent")
            doc.default_expense_account = cat.get("account")
            doc.insert()
            print(f"Created category: {cat['name']}")
    
    frappe.db.commit()
    print("Standard categories created.")

if __name__ == "__main__":
    create_standard_categories()
