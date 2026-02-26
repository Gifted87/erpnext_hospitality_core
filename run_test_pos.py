
import sys
import os

# Add bench paths
current_dir = os.getcwd()
# Assuming we are in apps/hospitality_core
bench_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(bench_dir)
sys.path.append(os.path.join(bench_dir, "apps/frappe"))
sys.path.append(os.path.join(bench_dir, "apps/hospitality_core"))

import frappe
from hospitality_core.hospitality_core.test_pos_restriction import test_pos_restriction

def main():
    try:
        frappe.init(site="hospitality")
        frappe.connect()
        test_pos_restriction()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if frappe.db:
            frappe.db.commit()
            frappe.destroy()

if __name__ == "__main__":
    main()
