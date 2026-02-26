#!/usr/bin/env python3
"""
Quick debug script to check auto-print functionality
Run with: bench execute hospitality_core.hospitality_core.debug_autoprint.check_autoprint
"""

import frappe

def check_autoprint():
    """Debug auto-print setup"""
    print("\n" + "="*60)
    print("AUTO-PRINT DEBUG CHECK")
    print("="*60)
    
    # 1. Check if module can be imported
    print("\n1. Checking module import...")
    try:
        from hospitality_core.hospitality_core.api.auto_print import auto_print_pos_invoice
        print("   ✓ auto_print module imported successfully")
    except Exception as e:
        print(f"   ✗ FAILED to import: {e}")
        return
    
    # 2. Check settings
    print("\n2. Checking Hospitality Accounting Settings...")
    try:
        settings = frappe.get_single("Hospitality Accounting Settings")
        print(f"   Enable Auto Print: {settings.enable_auto_print}")
        print(f"   Receipt Print Format: {settings.receipt_print_format or 'Standard'}")
        print(f"   Print Copies: {settings.print_copies or 3}")
        
        if not settings.enable_auto_print:
            print("\n   ⚠️  AUTO-PRINT IS DISABLED! Enable it in settings.")
    except Exception as e:
        print(f"   ✗ Error getting settings: {e}")
        return
    
    # 3. Check recent POS Invoices
    print("\n3. Checking recent POS Invoices...")
    try:
        recent = frappe.get_all(
            "POS Invoice",
            filters={"docstatus": 1},
            fields=["name", "posting_date", "creation"],
            order_by="creation desc",
            limit=3
        )
        if recent:
            print(f"   Found {len(recent)} recent submitted invoices:")
            for inv in recent:
                print(f"     - {inv.name} (created: {inv.creation})")
        else:
            print("   No submitted POS Invoices found")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 4. Check Error Logs
    print("\n4. Checking Error Logs for auto-print issues...")
    try:
        errors = frappe.get_all(
            "Error Log",
            filters=[
                ["error", "like", "%auto%print%"]
            ],
            fields=["name", "creation", "error"],
            order_by="creation desc",
            limit=3
        )
        if errors:
            print(f"   Found {len(errors)} auto-print related errors:")
            for err in errors:
                print(f"\n   Error: {err.name} ({err.creation})")
                # Print first 500 chars of error
                print(f"   {err.error[:500]}")
        else:
            print("   No auto-print errors found in Error Log")
    except Exception as e:
        print(f"   ✗ Error checking logs: {e}")
    
    # 5. Check hooks registration
    print("\n5. Checking hooks.py registration...")
    try:
        import hospitality_core.hospitality_core.hooks as hooks
        pos_hooks = hooks.doc_events.get("POS Invoice", {})
        on_submit = pos_hooks.get("on_submit", [])
        
        auto_print_hook = "hospitality_core.hospitality_core.api.auto_print.auto_print_pos_invoice"
        if auto_print_hook in on_submit:
            print(f"   ✓ Auto-print hook is registered")
        else:
            print(f"   ✗ Auto-print hook NOT found in on_submit hooks!")
            print(f"   Current on_submit hooks: {on_submit}")
    except Exception as e:
        print(f"   ✗ Error checking hooks: {e}")
    
    # 6. Test printer availability
    print("\n6. Checking system printer...")
    try:
        import subprocess
        result = subprocess.run(['lpstat', '-d'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"   {result.stdout.strip()}")
        else:
            print(f"   ✗ No default printer configured!")
            print(f"   Set one with: lpoptions -d <printer-name>")
    except Exception as e:
        print(f"   ✗ Error checking printer: {e}")
    
    print("\n" + "="*60)
    print("DEBUG CHECK COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    check_autoprint()
