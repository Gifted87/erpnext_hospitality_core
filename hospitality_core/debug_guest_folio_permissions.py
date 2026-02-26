#!/usr/bin/env python3
"""
Diagnostic script to investigate Guest Folio permission issues.
This will check:
1. DocPerm settings for Guest Folio
2. User Permissions that might restrict access
3. Whether users have restricted access based on the 'reserved_by' field
"""

import frappe

def execute():
    frappe.init(site="185.170.58.232", sites_path="/home/erpnext/frappe-bench/sites")
    frappe.connect()

    
    try:
        print("=" * 80)
        print("GUEST FOLIO PERMISSION DIAGNOSTIC")
        print("=" * 80)
        
        # 1. Check DocPerm settings
        print("\n1. DocPerm Settings for Guest Folio:")
        print("-" * 80)
        perms = frappe.db.sql("""
            SELECT role, `read`, `write`, `create`, `delete`, if_owner
            FROM `tabDocPerm`
            WHERE parent = 'Guest Folio'
            ORDER BY role
        """, as_dict=True)
        
        for perm in perms:
            print(f"  Role: {perm.role}")
            print(f"    Read: {perm.read}, Write: {perm.write}, Create: {perm.create}, Delete: {perm.delete}, If Owner: {perm.if_owner}")
        
        # 2. Check for User Permissions on Guest Folio
        print("\n2. User Permissions for Guest Folio:")
        print("-" * 80)
        user_perms = frappe.db.sql("""
            SELECT user, allow, for_value, apply_to_all_doctypes, applicable_for
            FROM `tabUser Permission`
            WHERE allow = 'Guest Folio'
        """, as_dict=True)
        
        if user_perms:
            print(f"  Found {len(user_perms)} User Permission records:")
            for up in user_perms:
                print(f"    User: {up.user}, Allow: {up.allow}, For Value: {up.for_value}")
                print(f"      Apply to All: {up.apply_to_all_doctypes}, Applicable For: {up.applicable_for}")
        else:
            print("  No User Permissions found for 'Guest Folio'")
        
        # 3. Check if there are User Permissions based on the User doctype
        # (This would restrict access based on the reserved_by field)
        print("\n3. User Permissions for User doctype (affects reserved_by field):")
        print("-" * 80)
        user_perms_on_user = frappe.db.sql("""
            SELECT user, allow, for_value, apply_to_all_doctypes, applicable_for
            FROM `tabUser Permission`
            WHERE allow = 'User'
        """, as_dict=True)
        
        if user_perms_on_user:
            print(f"  Found {len(user_perms_on_user)} User Permission records:")
            for up in user_perms_on_user:
                print(f"    User: {up.user}, Allow: {up.allow}, For Value: {up.for_value}")
                print(f"      Apply to All: {up.apply_to_all_doctypes}, Applicable For: {up.applicable_for}")
        else:
            print("  No User Permissions found for 'User' doctype")
        
        # 4. Check Guest Folio records with reserved_by field
        print("\n4. Sample Guest Folio records with reserved_by:")
        print("-" * 80)
        folios = frappe.db.sql("""
            SELECT name, guest, reserved_by, status
            FROM `tabGuest Folio`
            ORDER BY modified DESC
            LIMIT 10
        """, as_dict=True)
        
        for folio in folios:
            print(f"  Folio: {folio.name}, Guest: {folio.guest}, Reserved By: {folio.reserved_by}, Status: {folio.status}")
        
        # 5. Suggest solutions
        print("\n" + "=" * 80)
        print("SUGGESTED SOLUTIONS:")
        print("=" * 80)
        print("If User Permissions on 'User' doctype exist and restrict access:")
        print("  - Option 1: Remove User Permissions for User doctype")
        print("  - Option 2: Add permission_query hook to bypass reserved_by restriction")
        print("  - Option 3: Don't use reserved_by as a Link field, use Data field instead")
        print("\nIf if_owner is set to 1 in DocPerm:")
        print("  - Set if_owner to 0 for Hospitality User role")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        frappe.destroy()

if __name__ == "__main__":
    execute()
