"""
Simple test to manually trigger auto-print
Run in bench console:
  bench console
  
Then paste this:
  exec(open('apps/hospitality_core/hospitality_core/test_manual_print.py').read())
"""

import frappe

def test_manual_autoprint():
    print("\n=== Manual Auto-Print Test ===\n")
    
    # Import the function
    from hospitality_core.hospitality_core.api.auto_print import auto_print_pos_invoice
    
    # Get settings
    settings = frappe.get_single("Hospitality Accounting Settings")
    print(f"Auto-print enabled: {settings.enable_auto_print}")
    print(f"Print format: {settings.receipt_print_format or 'Standard'}")
    print(f"Copies: {settings.print_copies or 3}")
    
    if not settings.enable_auto_print:
        print("\n⚠️  Auto-print is DISABLED in settings!")
        print("Enable it in Hospitality Accounting Settings\n")
        return
    
    # Get most recent submitted POS Invoice
    invoice_name = frappe.get_value("POS Invoice", {"docstatus": 1}, "name", order_by="creation desc")
    
    if not invoice_name:
        print("\n⚠️  No submitted POS Invoices found!")
        print("Create and submit a POS Invoice first\n")
        return
    
    print(f"\nTesting with invoice: {invoice_name}")
    
    # Get the doc
    doc = frappe.get_doc("POS Invoice", invoice_name)
    
    # Manually call the function
    print("\nCalling auto_print_pos_invoice()...")
    try:
        auto_print_pos_invoice(doc, "on_submit")
        print("✓ Function executed successfully!")
        print("\nCheck:")
        print("  1. Print queue: lpstat -o")
        print("  2. Error Log for any errors")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_manual_autoprint()
else:
    # When exec'd in console
    test_manual_autoprint()
