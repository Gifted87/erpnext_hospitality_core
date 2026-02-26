"""
Data Cleanup Script
Deletes Payment Entries, Hotel Reservations, Guest Folios, and POS Invoices
created from January 22, 2026 onwards.

WARNING: This is a DESTRUCTIVE operation. Make sure to backup your database first!

Usage:
    bench --site <sitename> execute hospitality_core.hospitality_core.cleanup_jan22_data.cleanup_data
"""

import frappe
from frappe import _
from datetime import datetime

# Define the cutoff date
CUTOFF_DATE = "2026-01-22"

def cleanup_data(dry_run=True):
    """
    Delete all specified data from January 22, 2026 onwards.
    
    Args:
        dry_run (bool): If True, only shows what would be deleted without actually deleting
    """
    print("\n" + "="*70)
    print("DATA CLEANUP SCRIPT")
    print(f"Cutoff Date: {CUTOFF_DATE}")
    print(f"Mode: {'DRY RUN (no actual deletion)' if dry_run else 'LIVE (will delete data)'}")
    print("="*70 + "\n")
    
    if not dry_run:
        response = input("⚠️  WARNING: This will PERMANENTLY delete data! Type 'DELETE' to confirm: ")
        if response != "DELETE":
            print("\n❌ Cleanup cancelled.\n")
            return
    
    stats = {
        "pos_invoices": 0,
        "payment_entries": 0,
        "folio_transactions": 0,
        "guest_folios": 0,
        "hotel_reservations": 0
    }
    
    errors = []
    
    try:
        # 1. Delete POS Invoices
        print("\n1. Processing POS Invoices...")
        stats["pos_invoices"] = delete_pos_invoices(dry_run, errors)
        
        # 2. Delete Payment Entries
        print("\n2. Processing Payment Entries...")
        stats["payment_entries"] = delete_payment_entries(dry_run, errors)
        
        # 3. Delete Folio Transactions (must be before Guest Folios)
        print("\n3. Processing Folio Transactions...")
        stats["folio_transactions"] = delete_folio_transactions(dry_run, errors)
        
        # 4. Delete Guest Folios
        print("\n4. Processing Guest Folios...")
        stats["guest_folios"] = delete_guest_folios(dry_run, errors)
        
        # 5. Delete Hotel Reservations
        print("\n5. Processing Hotel Reservations...")
        stats["hotel_reservations"] = delete_hotel_reservations(dry_run, errors)
        
        # Print summary
        print("\n" + "="*70)
        print("CLEANUP SUMMARY")
        print("="*70)
        print(f"POS Invoices:         {stats['pos_invoices']}")
        print(f"Payment Entries:      {stats['payment_entries']}")
        print(f"Folio Transactions:   {stats['folio_transactions']}")
        print(f"Guest Folios:         {stats['guest_folios']}")
        print(f"Hotel Reservations:   {stats['hotel_reservations']}")
        print(f"\nTotal Deleted:        {sum(stats.values())}")
        
        if errors:
            print(f"\n⚠️  Errors encountered: {len(errors)}")
            print("\nFirst 5 errors:")
            for err in errors[:5]:
                print(f"  - {err}")
        
        print("="*70 + "\n")
        
        if dry_run:
            print("ℹ️  This was a DRY RUN. No data was actually deleted.")
            print("   To perform actual deletion, run:")
            print("   cleanup_data(dry_run=False)\n")
        else:
            print("✅ Cleanup completed!\n")
            frappe.db.commit()
        
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        if not dry_run:
            frappe.db.rollback()
        raise


def delete_pos_invoices(dry_run, errors):
    """Delete POS Invoices from cutoff date"""
    invoices = frappe.get_all(
        "POS Invoice",
        filters={"creation": [">=", CUTOFF_DATE]},
        fields=["name", "docstatus"]
    )
    
    print(f"   Found {len(invoices)} POS Invoices to delete")
    
    deleted = 0
    for inv in invoices:
        try:
            if not dry_run:
                doc = frappe.get_doc("POS Invoice", inv.name)
                
                # Cancel if submitted
                if doc.docstatus == 1:
                    doc.cancel()
                    print(f"   Cancelled: {inv.name}")
                
                # Delete
                frappe.delete_doc("POS Invoice", inv.name, force=True)
            
            deleted += 1
            if deleted % 10 == 0:
                print(f"   Processed {deleted}/{len(invoices)}...")
        except Exception as e:
            errors.append(f"POS Invoice {inv.name}: {str(e)}")
    
    print(f"   ✓ Deleted {deleted} POS Invoices")
    return deleted


def delete_payment_entries(dry_run, errors):
    """Delete Payment Entries from cutoff date"""
    payments = frappe.get_all(
        "Payment Entry",
        filters={"creation": [">=", CUTOFF_DATE]},
        fields=["name", "docstatus"]
    )
    
    print(f"   Found {len(payments)} Payment Entries to delete")
    
    deleted = 0
    for pay in payments:
        try:
            if not dry_run:
                doc = frappe.get_doc("Payment Entry", pay.name)
                
                # Cancel if submitted
                if doc.docstatus == 1:
                    doc.cancel()
                    print(f"   Cancelled: {pay.name}")
                
                # Delete
                frappe.delete_doc("Payment Entry", pay.name, force=True)
            
            deleted += 1
            if deleted % 10 == 0:
                print(f"   Processed {deleted}/{len(payments)}...")
        except Exception as e:
            errors.append(f"Payment Entry {pay.name}: {str(e)}")
    
    print(f"   ✓ Deleted {deleted} Payment Entries")
    return deleted


def delete_folio_transactions(dry_run, errors):
    """Delete Folio Transactions from cutoff date"""
    transactions = frappe.get_all(
        "Folio Transaction",
        filters={"creation": [">=", CUTOFF_DATE]},
        fields=["name"]
    )
    
    print(f"   Found {len(transactions)} Folio Transactions to delete")
    
    deleted = 0
    for txn in transactions:
        try:
            if not dry_run:
                frappe.delete_doc("Folio Transaction", txn.name, force=True)
            
            deleted += 1
            if deleted % 50 == 0:
                print(f"   Processed {deleted}/{len(transactions)}...")
        except Exception as e:
            errors.append(f"Folio Transaction {txn.name}: {str(e)}")
    
    print(f"   ✓ Deleted {deleted} Folio Transactions")
    return deleted


def delete_guest_folios(dry_run, errors):
    """Delete Guest Folios from cutoff date"""
    folios = frappe.get_all(
        "Guest Folio",
        filters={"creation": [">=", CUTOFF_DATE]},
        fields=["name"]
    )
    
    print(f"   Found {len(folios)} Guest Folios to delete")
    
    deleted = 0
    for folio in folios:
        try:
            if not dry_run:
                # Delete remaining child transactions first
                frappe.db.delete("Folio Transaction", {"parent": folio.name})
                # Delete folio
                frappe.delete_doc("Guest Folio", folio.name, force=True)
            
            deleted += 1
            if deleted % 10 == 0:
                print(f"   Processed {deleted}/{len(folios)}...")
        except Exception as e:
            errors.append(f"Guest Folio {folio.name}: {str(e)}")
    
    print(f"   ✓ Deleted {deleted} Guest Folios")
    return deleted


def delete_hotel_reservations(dry_run, errors):
    """Delete Hotel Reservations from cutoff date"""
    reservations = frappe.get_all(
        "Hotel Reservation",
        filters={"creation": [">=", CUTOFF_DATE]},
        fields=["name", "docstatus"]
    )
    
    print(f"   Found {len(reservations)} Hotel Reservations to delete")
    
    deleted = 0
    for res in reservations:
        try:
            if not dry_run:
                doc = frappe.get_doc("Hotel Reservation", res.name)
                
                # Cancel if submitted
                if doc.docstatus == 1:
                    doc.cancel()
                    print(f"   Cancelled: {res.name}")
                
                # Delete
                frappe.delete_doc("Hotel Reservation", res.name, force=True)
            
            deleted += 1
            if deleted % 10 == 0:
                print(f"   Processed {deleted}/{len(reservations)}...")
        except Exception as e:
            errors.append(f"Hotel Reservation {res.name}: {str(e)}")
    
    print(f"   ✓ Deleted {deleted} Hotel Reservations")
    return deleted


if __name__ == "__main__":
    # Run in dry-run mode by default
    cleanup_data(dry_run=True)
