#!/usr/bin/env python3
"""
Test script to verify Guest Folio permissions after the fix.
This will simulate permission checks for different user roles.
"""

import frappe

def test_permission():
    frappe.init(site="185.170.58.232", sites_path="/home/erpnext/frappe-bench/sites")
    frappe.connect()
    
    try:
        print("=" * 80)
        print("GUEST FOLIO PERMISSION TEST")
        print("=" * 80)
        
        # Get the has_permission method from GuestFolio
        from hospitality_core.hospitality_core.doctype.guest_folio.guest_folio import GuestFolio
        
        # Get all users with Hospitality User role
        hospitality_users = frappe.db.sql("""
            SELECT DISTINCT parent as user
            FROM `tabHas Role`
            WHERE role = 'Hospitality User'
            AND parenttype = 'User'
        """, as_dict=True)
        
        print(f"\nFound {len(hospitality_users)} Hospitality Users")
        
        # Get a sample Guest Folio
        sample_folio = frappe.db.get_value("Guest Folio", {}, ["name", "reserved_by"], as_dict=True)
        
        if sample_folio:
            print(f"\nTesting with sample folio: {sample_folio.name}")
            print(f"Reserved by: {sample_folio.reserved_by}")
            
            # Test permission for each hospitality user
            for user_rec in hospitality_users[:5]:  # Test first 5 users
                user = user_rec.user
                has_perm = GuestFolio.has_permission(sample_folio.name, 'read', user)
                print(f"\n  User: {user}")
                print(f"  Can access folio: {has_perm}")
                
                if has_perm:
                    print(f"  ✓ SUCCESS: User can access the folio")
                else:
                    print(f"  ✗ FAIL: User cannot access the folio")
        else:
            print("\nNo guest folios found in the system to test with")
        
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        print("\nIf all Hospitality Users show 'Can access folio: True',")
        print("then the permission fix is working correctly!")
        
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        frappe.destroy()

if __name__ == "__main__":
    test_permission()
