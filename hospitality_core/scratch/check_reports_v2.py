import frappe

def check_reports():
    reports = frappe.db.get_all("Report", 
        fields=["name", "report_name", "module"]
    )
    for r in reports:
        if "End of Day" in r.name:
            print(f"Report: {r.name} | Module: {r.module} | Report Name: {r.report_name}")

if __name__ == "__main__":
    check_reports()
