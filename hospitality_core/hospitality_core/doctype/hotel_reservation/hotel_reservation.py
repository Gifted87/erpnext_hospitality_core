import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, add_days, flt, now_datetime
from hospitality_core.hospitality_core.api.reservation import check_availability, create_folio
# Imports for immediate billing logic
from hospitality_core.hospitality_core.api.night_audit import post_room_charge, get_rate, already_charged_today

class HotelReservation(Document):
    def validate(self):
        if not self.is_company_guest:
            self.company = None

        self.validate_dates()
        
        # Only validate availability if status is Reserved or Checked In
        if self.status in ["Reserved", "Checked In"]:
            self.validate_room_availability()
        
        # Requirement: "billing to Company should be set... Folio is opened to the Company"
        # New Requirement: If Is Company Guest is checked, Company is mandatory
        if self.is_company_guest and not self.company:
            frappe.throw(_("Company is mandatory when 'Is Company Guest' is checked."))

        if self.company:
            self.ensure_company_folio()

    def validate_dates(self):
        if getdate(self.arrival_date) >= getdate(self.departure_date):
            frappe.throw(_("Departure Date must be after Arrival Date."))

    def validate_room_availability(self):
        check_availability(
            room=self.room, 
            arrival_date=self.arrival_date, 
            departure_date=self.departure_date, 
            ignore_reservation=self.name
        )

    def before_insert(self):
        self.reserved_by = frappe.session.user

    def after_insert(self):
        # Requirement: "And a Folio is also opened for the guest"
        create_folio(self)

    def ensure_company_folio(self):
        """
        Ensures an OPEN Master Folio exists for the Company.
        Company Folios are indefinite and manually closed.
        """
        if not self.company:
            return

        # Check for existing Open Master Folio for this Company
        exists = frappe.db.exists("Guest Folio", {
            "company": self.company,
            "status": "Open",
            "is_company_master": 1
        })

        if not exists:
            # Create Master Company Folio
            guest_name = self.get_corporate_guest_name()
            
            folio = frappe.new_doc("Guest Folio")
            folio.is_company_master = 1 # Flag as Company Folio
            folio.guest = guest_name
            folio.company = self.company
            folio.status = "Open"
            folio.open_date = nowdate()
            # No specific reservation/room link for Master Folio
            folio.insert(ignore_permissions=True)
            frappe.msgprint(_("Created new Master Folio for Company: {0}").format(self.company))

    def get_corporate_guest_name(self):
        """
        Gets or creates a Representative Guest record for the Company to attach the Master Folio to.
        """
        g_name = frappe.db.get_value("Guest", {"customer": self.company}, "name")
        if not g_name:
            # Create a placeholder guest for the company
            cust = frappe.get_doc("Customer", self.company)
            g = frappe.new_doc("Guest")
            g.full_name = cust.customer_name + " (Master Rep)"
            g.customer = self.company
            g.guest_type = "Corporate"
            g.insert(ignore_permissions=True)
            g_name = g.name
        return g_name

    def process_check_in(self):
        """
        Transition: Reserved -> Checked In
        Room: Available -> Occupied
        Folio: Provisional -> Open
        Action: CHARGE FIRST NIGHT IMMEDIATELY
        """
        if self.status != "Reserved":
            frappe.throw(_("Only Reserved bookings can be Checked In."))
        
        if getdate(self.arrival_date) > getdate(nowdate()):
            frappe.throw(_("Cannot Check-In before Arrival Date."))

        # 1. Update Reservation and Folio in a single process
        # We use db_set to avoid triggering the full 'save' cycle which might be overkill here
        # but since we have other fields to update (in check-in it's just status), it's fine.
        self.status = "Checked In"
        
        # 2. Update Room Status
        frappe.db.set_value("Hotel Room", self.room, "status", "Occupied")
        
        # 3. Update Folio Status
        if self.folio:
            frappe.db.set_value("Guest Folio", self.folio, "status", "Open")

            # 4. IMMEDIATE CHARGE
            # Hospitality Day Logic: Check-in before 8:00 AM counts as "Yesterday"
            current_hour = now_datetime().hour
            charge_date = nowdate()
            if current_hour < 8:
                charge_date = add_days(nowdate(), -1)

            if not already_charged_today(self.folio, charge_date, room=self.room):
                rate = get_rate(self.rate_plan, self.room_type, charge_date)
                if rate > 0:
                    post_room_charge(self, rate, charge_date)
                    frappe.msgprint(_("Check-in successful. Room charged {0} for date {1}.").format(rate, charge_date))
        
        self.save()
        return "Checked In"

    def process_check_out(self):
        """
        Transition: Checked In -> Checked Out
        Room: Occupied -> Dirty
        Folio: Validate Balance -> Closed -> SUBMITTED (Immutable)
        Reservation: SUBMITTED (Immutable)
        """
        if self.status != "Checked In":
            frappe.throw(_("Guest is not currently Checked In."))

        if getdate(self.departure_date) != getdate(nowdate()):
            frappe.throw(_("Cannot Check Out. Departure date ({0}) must be today ({1}).").format(self.departure_date, nowdate()))

        # Requirement: "When a reservation is part of a group booking, that reservation cannot be checked out until the master folio is cleared."
        if self.is_group_guest and self.group_booking:
            master_folio = frappe.db.get_value("Hotel Group Booking", self.group_booking, "master_folio")
            if master_folio:
                # Sync balance to get latest totals
                master_folio_doc = frappe.get_doc("Guest Folio", master_folio)
                from hospitality_core.hospitality_core.api.folio import sync_folio_balance
                sync_folio_balance(master_folio_doc)
                
                # Re-fetch balance
                master_balance = frappe.db.get_value("Guest Folio", master_folio, "outstanding_balance")
                if master_balance > 0.01:
                    frappe.throw(_("Cannot Check Out. The Group Master Folio ({0}) has an outstanding balance of {1}. All group charges must be settled first.").format(master_folio, master_balance))

        # 1. Handle Folio
        if self.folio:
            # Check status first - if Closed, we skip all operations to avoid "Cannot add transactions" error
            folio_status = frappe.db.get_value("Guest Folio", self.folio, "status")
            
            if folio_status == "Closed":
                frappe.msgprint(_("Guest Folio {0} is already Closed. Skipping financial updates.").format(self.folio))
            else:
                folio_doc = frappe.get_doc("Guest Folio", self.folio)
                
                # --- START: AUTOMATIC TRANSFER TO CITY LEDGER ---
                if self.company:
                    # Calculate total amount tagged as 'Bill To Company' on this folio
                    company_liability = frappe.db.sql("""
                        SELECT SUM(amount) FROM `tabFolio Transaction`
                        WHERE parent = %s 
                        AND bill_to = 'Company' 
                        AND is_void = 0
                    """, (self.folio,), as_dict=False)[0][0] or 0.0

                    if company_liability > 0:
                        # Check if we already posted a transfer to avoid double credit if button clicked twice
                        transfer_item = "TRANSFER"
                        if not frappe.db.exists("Item", transfer_item):
                            item = frappe.new_doc("Item")
                            item.item_code = transfer_item
                            item.item_name = "Transfer to City Ledger"
                            item.item_group = "Services"
                            item.is_stock_item = 0
                            item.insert(ignore_permissions=True)
                        
                        transfer_exists = frappe.db.exists("Folio Transaction", {
                            "parent": self.folio,
                            "item": transfer_item,
                            "posting_date": nowdate(),
                            "amount": -1 * flt(company_liability)
                        })

                        if not transfer_exists:
                            # Create the Credit Transaction on Guest Folio
                            # This zeros out the Company portion on the Guest's view
                            frappe.get_doc({
                                "doctype": "Folio Transaction",
                                "parent": self.folio,
                                "parenttype": "Guest Folio",
                                "parentfield": "transactions",
                                "posting_date": nowdate(),
                                "item": transfer_item,
                                "description": f"Transfer to Master Folio (City Ledger) - {self.company}",
                                "qty": 1,
                                "amount": -1 * flt(company_liability), # Credit
                                "bill_to": "Company",
                                "is_void": 0
                            }).insert(ignore_permissions=True)
                            
                            frappe.msgprint(_("Transferred {0} to City Ledger.").format(company_liability))
                # --- END: AUTOMATIC TRANSFER ---

                # --- START: AUTOMATIC TRANSFER TO GROUP MASTER ---
                if self.is_group_guest and self.group_booking:
                    # 1. Get Group Master Folio ID
                    group_master_folio = frappe.db.get_value("Hotel Group Booking", self.group_booking, "master_folio")
                    
                    if group_master_folio and group_master_folio != self.folio:
                        # 2. Calculate total liability on Guest Folio (excluding existing transfers)
                        # Re-sync balance first
                        from hospitality_core.hospitality_core.api.folio import sync_folio_balance
                        sync_folio_balance(folio_doc)
                        current_balance = frappe.db.get_value("Guest Folio", self.folio, "outstanding_balance")
                        
                        if current_balance > 0.01:
                            transfer_item = "TRANSFER-GROUP"
                            if not frappe.db.exists("Item", transfer_item):
                                item = frappe.new_doc("Item")
                                item.item_code = transfer_item
                                item.item_name = "Transfer to Group Master"
                                item.item_group = "Services"
                                item.is_stock_item = 0
                                item.insert(ignore_permissions=True)
                                
                            # 3. Credit Guest Folio to zero it out for checkout
                            # This transaction will NOT be mirrored to the Master Folio 
                            # (handled by skip logic in folio.py)
                            frappe.get_doc({
                                "doctype": "Folio Transaction",
                                "parent": self.folio,
                                "parenttype": "Guest Folio",
                                "parentfield": "transactions",
                                "posting_date": nowdate(),
                                "item": transfer_item,
                                "description": f"Internal Balance Settlement (Group Bill) - {self.group_booking}",
                                "qty": 1,
                                "amount": -1 * flt(current_balance), # Credit
                                "bill_to": "Group",
                                "is_void": 0
                            }).insert(ignore_permissions=True)
                            
                            frappe.msgprint(_("Individual balance of {0} settled via Group Master.").format(current_balance))
                # --- END: AUTOMATIC TRANSFER TO GROUP MASTER ---
                
                # Recalculate balance - NOTE: transfer transaction inserts above already triggered sync via hooks!
                from hospitality_core.hospitality_core.api.folio import sync_folio_balance
                sync_folio_balance(folio_doc)
                
                # Get latest balance from DB (sync_folio_balance updates DB directly)
                balance = frappe.db.get_value("Guest Folio", self.folio, "outstanding_balance")
                
                # Requirement: "folio once opened cannot be closed until all payments are made... enforced... for private guests"
                # Updated Requirement: Company Guests can check out with balance.
                
                if not self.is_company_guest:
                    if balance > 0.01:
                        frappe.throw(_("Cannot Check Out. Outstanding balance of {0} remains on Folio {1}. Please settle payment.").format(balance, self.folio))
                else:
                    if balance > 0.01:
                        frappe.msgprint(_("Company Guest Checkout: Outstanding balance of {0}. Liability remains on Company Master Folio.").format(balance))
                
                # Close Folio using db_set to avoid timestamp conflicts
                # (Transaction inserts trigger sync_folio_balance hooks which update DB timestamps)
                frappe.db.set_value("Guest Folio", self.folio, {
                    "status": "Closed",
                    "close_date": nowdate()
                })
                
                # Record guest balance if there's a credit balance
                # (after_save hook handles this, but we call it explicitly to ensure it runs)
                from hospitality_core.hospitality_core.api.folio import record_guest_balance
                record_guest_balance(folio_doc)

        # 2. Update Reservation Status
        # Use db_set to avoid "Document has been modified" errors caused by background updates 
        # (e.g. from Folio/Room logic) triggering optimistic locking failures during full save.
        self.db_set("status", "Checked Out")
        
        # 3. Update Room Status to Dirty
        frappe.db.set_value("Hotel Room", self.room, "status", "Dirty")

        # 4. No self.save() needed - db_set handles the status update safely.

        return "Checked Out"
    
    def process_cancel(self):
        """
        Transition: Reserved -> Cancelled
        """
        if self.status not in ["Reserved", "Checked In"]:
            frappe.throw(_("Only Reserved or Checked In bookings can be Cancelled."))
        
        self.db_set("status", "Cancelled")
        
        # If there's a folio, cancel it as well if it's not already closed
        if self.folio:
            folio_status = frappe.db.get_value("Guest Folio", self.folio, "status")
            if folio_status not in ["Closed", "Cancelled"]:
                frappe.db.set_value("Guest Folio", self.folio, "status", "Cancelled")
                frappe.msgprint(_("Linked Guest Folio {0} has been cancelled.").format(self.folio))
        
        return "Cancelled"

# Whitelisted methods for client-side buttons
@frappe.whitelist()
def check_in_guest(name):
    doc = frappe.get_doc("Hotel Reservation", name)
    return doc.process_check_in()

@frappe.whitelist()
def check_out_guest(name):
    doc = frappe.get_doc("Hotel Reservation", name)
    return doc.process_check_out()

@frappe.whitelist()
def cancel_reservation(name):
    doc = frappe.get_doc("Hotel Reservation", name)
    return doc.process_cancel()