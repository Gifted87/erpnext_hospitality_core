import frappe

def check_reports():
    reports = frappe.db.get_all("Report", 
        filters={"name": ["like", "%End of Day%"]},
        fields=["name", "module", "report_name", "is_standard"]
    )
    for r in reports:
        print(f"Report Found: {r}")

if __name__ == "__main__":
    check_reports()
