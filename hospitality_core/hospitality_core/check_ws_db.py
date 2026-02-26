
import frappe
import json

def check():
    ws = frappe.get_doc("Workspace", "Hospitality")
    print(f"Workspace: {ws.label}")
    for link in ws.links:
        if "Departures" in link.label:
            print(f"Label: {link.label}")
            print(f" - link_type: {link.link_type}")
            print(f" - link_to: {link.link_to}")
            print(f" - is_query_report: {link.is_query_report}")
            print(f" - report_ref_doctype: {link.report_ref_doctype}")

if __name__ == "__main__":
    check()
