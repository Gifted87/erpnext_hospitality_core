import frappe
from hospitality_core.hospitality_core.final_fix import run_final_migration

def main():
    site = "185.170.58.232"
    frappe.init(site=site)
    frappe.connect()
    try:
        run_final_migration()
    finally:
        frappe.destroy()

if __name__ == "__main__":
    main()
