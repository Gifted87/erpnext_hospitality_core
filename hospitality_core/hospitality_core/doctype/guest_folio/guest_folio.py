import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname

class GuestFolio(Document):
    def autoname(self):
        # Different Naming for Company Master Folios
        if self.is_company_master:
            # e.g., MASTER-GOOGLE
            # We sanitize the company name
            company_key = self.company.replace(" ", "")[:10].upper()
            self.name = make_autoname(f"MASTER-{company_key}-.#####")
        else:
            # Standard Guest Folio: FOLIO-RES-GUEST
            if self.reservation:
                self.name = make_autoname("FOLIO-.#####")
            else:
                self.name = make_autoname("FOLIO-.#####")

    def validate(self):
        # Enforce chronological order of transactions
        if self.transactions:
            self.transactions.sort(key=lambda x: (x.posting_date or "", x.creation or ""))
            for i, d in enumerate(self.transactions):
                d.idx = i + 1
            
        self.validate_status_change()
        self.validate_master_folio()

    def validate_master_folio(self):
        if self.is_company_master and not self.company:
            frappe.throw(_("Company is mandatory for a Company Master Folio."))
        
        if not self.is_company_master and not self.reservation:
            # Regular guest folios usually need a reservation
            pass

    def validate_status_change(self):
        if self.status == "Closed":
            # Check if this folio belongs to a Company Guest
            is_company_guest = False
            if self.reservation:
                is_company_guest = frappe.db.get_value("Hotel Reservation", self.reservation, "is_company_guest")
            
            # If it is NOT a company guest, strict balance enforcement applies.
            # If it IS a company guest, we assume the balance is liable to the company and allow closure.
            if not is_company_guest:
                # Only prevent closure if there is a DEBIT balance (guest owes money)
                # CREDIT balances (guest is owed money) are recorded in the Guest Balance Ledger.
                if self.outstanding_balance > 0.01:
                    frappe.throw(
                        _("Cannot Close Folio. Outstanding Balance is {0}. Please settle payments or post allowances.").format(self.outstanding_balance)
                    )

    def after_save(self):
        if self.status == "Closed":
            from hospitality_core.hospitality_core.api.folio import record_guest_balance
            record_guest_balance(self)

    def on_trash(self):
        if self.transactions:
            frappe.throw(_("Cannot delete a Folio that has transactions. Cancel it instead."))
    
    def has_permission(self, ptype="read", user=None):
        """
        Custom permission check for Guest Folio.
        
        This method overrides Frappe's default permission logic to ensure that
        all Hospitality Users can access all guest folios, regardless of the
        'reserved_by' field which links to the User doctype.
        
        Without this override, Frappe's User Permission system would restrict
        access based on which User records a user can access, causing receptionists
        to only see folios they created themselves.
        
        Args:
            ptype: Permission type ('read', 'write', 'delete', etc.)
            user: The user requesting access (defaults to current user)
            
        Returns:
            True if access should be granted, False otherwise
        """
        if not user:
            user = frappe.session.user
        
        # System Managers and Administrators always have full access
        if "System Manager" in frappe.get_roles(user) or "Administrator" in frappe.get_roles(user):
            return True
        
        # Hospitality Users should have access to all folios regardless of reserved_by
        if "Hospitality User" in frappe.get_roles(user):
            return True
        
        # For other roles, use default permission logic
        return False