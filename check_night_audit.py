#!/usr/bin/env python3
"""
Diagnostic script to check night audit status and manually trigger it
"""
import frappe
from frappe.utils import nowdate, getdate
from hospitality_core.hospitality_core.api.night_audit import run_daily_audit, already_charged_today

def main():
    # Initialize Frappe
    frappe.init(site='site1.local')
    frappe.connect()
    
    print("\n=== NIGHT AUDIT DIAGNOSTIC ===\n")
    print(f"Current Date: {nowdate()}")
    print(f"Current Time: {frappe.utils.now()}")
    
    # Check if scheduler is enabled
    scheduler_enabled = frappe.db.get_single_value("System Settings", "enable_scheduler")
    print(f"\nScheduler Enabled: {scheduler_enabled}")
    
    # Get all checked-in reservations
    reservations = frappe.get_all("Hotel Reservation",
        filters={"status": "Checked In"},
        fields=["name", "guest", "room", "room_type", "folio", "departure_date"]
    )
    
    print(f"\nChecked-In Reservations: {len(reservations)}")
    
    if reservations:
        print("\nReservation Details:")
        for i, res in enumerate(reservations, 1):
            print(f"{i}. {res.name} - Guest: {res.guest}, Room: {res.room}")
            
            # Check if already billed today
            already_billed = already_charged_today(res.folio, nowdate(), room=res.room)
            print(f"   Already billed today: {already_billed}")
    
    # Check recent error logs
    print("\n=== Recent Night Audit Errors ===")
    error_logs = frappe.get_all("Error Log",
        filters={"error": ["like", "%Night Audit%"]},
        fields=["name", "creation", "error"],
        order_by="creation desc",
        limit=5
    )
    
    if error_logs:
        for log in error_logs:
            print(f"\n{log.creation}: {log.name}")
            print(f"Error: {log.error[:200]}...")
    else:
        print("No recent night audit errors found")
    
    # Ask if user wants to run it manually
    print("\n" + "="*50)
    response = input("\nDo you want to run the night audit manually now? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        print("\nRunning night audit...")
        try:
            run_daily_audit()
            frappe.db.commit()
            print("✓ Night audit completed successfully!")
        except Exception as e:
            print(f"✗ Error running night audit: {str(e)}")
            frappe.log_error(frappe.get_traceback(), "Manual Night Audit Error")
    else:
        print("\nSkipping manual run.")
    
    frappe.destroy()

if __name__ == "__main__":
    main()
