"""
Debug script to test automatic printing functionality
"""
import frappe

def test_auto_print():
    print("=== Testing Auto Print Functionality ===\n")
    
    # 1. Check if auto_print module can be imported
    try:
        from hospitality_core.hospitality_core.api.auto_print import auto_print_pos_invoice, send_print_job
        print("✓ auto_print module imported successfully")
    except Exception as e:
        print(f"✗ Failed to import auto_print module: {e}")
        return
    
    # 2. Check Hospitality Accounting Settings
    try:
        settings = frappe.get_single("Hospitality Accounting Settings")
        print(f"\n--- Hospitality Accounting Settings ---")
        print(f"Enable Auto Print: {settings.enable_auto_print}")
        print(f"Receipt Print Format: {settings.receipt_print_format or 'Standard'}")
        print(f"Print Copies: {settings.print_copies or 3}")
    except Exception as e:
        print(f"✗ Failed to get settings: {e}")
        return
    
    # 3. Check if there are recent POS Invoices
    try:
        recent_invoices = frappe.get_all(
            "POS Invoice",
            filters={"docstatus": 1},
            fields=["name", "posting_date", "grand_total"],
            order_by="creation desc",
            limit=5
        )
        print(f"\n--- Recent POS Invoices (Submitted) ---")
        if recent_invoices:
            for inv in recent_invoices:
                print(f"  {inv.name} - {inv.posting_date} - {inv.grand_total}")
        else:
            print("  No submitted POS Invoices found")
    except Exception as e:
        print(f"✗ Failed to get invoices: {e}")
    
    # 4. Check Error Log for auto print errors
    try:
        errors = frappe.get_all(
            "Error Log",
            filters={"error": ["like", "%Auto Print%"]},
            fields=["name", "creation", "error"],
            order_by="creation desc",
            limit=3
        )
        print(f"\n--- Auto Print Error Logs ---")
        if errors:
            for err in errors:
                print(f"\n{err.name} - {err.creation}")
                print(f"{err.error[:300]}...")
        else:
            print("  No auto print errors found")
    except Exception as e:
        print(f"✗ Failed to get error logs: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_auto_print()
