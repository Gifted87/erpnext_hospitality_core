#!/bin/bash
# Simple test script for auto-print
# Usage: bash test_autoprint.sh

cd /home/erpnext/frappe-bench

echo "==============================================="
echo "Testing Auto-Print Functionality"
echo "==============================================="
echo ""

# Test with bench console
bench --site 185.170.58.232 console << 'PYTHON_CODE'

print("\n=== AUTO-PRINT DEBUG ===\n")

# 1. Check module import
try:
    from hospitality_core.hospitality_core.api.auto_print import auto_print_pos_invoice
    print("✓ auto_print module imported")
except Exception as e:
    print(f"✗ Failed to import: {e}")
    exit()

# 2. Check settings
import frappe
settings = frappe.get_single("Hospitality Accounting Settings")
print(f"\n--- Settings ---")
print(f"Auto-print enabled: {settings.enable_auto_print}")
print(f"Print format: {settings.receipt_print_format or 'Standard'}")
print(f"Copies: {settings.print_copies or 3}")

if not settings.enable_auto_print:
    print("\n⚠️  AUTO-PRINT IS DISABLED!")
    print("Enable it in: Hospitality Accounting Settings\n")
    exit()

# 3. Check for recent invoices
invoices = frappe.get_all("POS Invoice", {"docstatus": 1}, ["name", "creation"], order_by="creation desc", limit=3)
print(f"\n--- Recent Invoices ---")
if invoices:
    for inv in invoices:
        print(f"  {inv.name}")
else:
    print("  None found")

# 4. Check errors
errors = frappe.get_all("Error Log", [["error", "like", "%auto%print%"]], ["name", "creation"], order_by="creation desc", limit=2)
print(f"\n--- Errors ---")
if errors:
    for err in errors:
        print(f"  {err.name} - {err.creation}")
        full_err = frappe.get_doc("Error Log", err.name)
        print(f"  {full_err.error[:200]}")
else:
    print("  No errors found")

# 5. Test with most recent invoice
if invoices:
    invoice_name = invoices[0].name
    print(f"\n--- Testing with {invoice_name} ---")
    doc = frappe.get_doc("POS Invoice", invoice_name)
    try:
        auto_print_pos_invoice(doc, "on_submit")
        print("✓ Auto-print function executed")
        print("\nCheck print queue: lpstat -o")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

print("\n=== TEST COMPLETE ===\n")

PYTHON_CODE
