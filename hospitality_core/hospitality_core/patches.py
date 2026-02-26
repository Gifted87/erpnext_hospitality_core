import frappe
import erpnext.accounts.party
import erpnext.accounts.doctype.gl_entry.gl_entry

# Monkey Patch: Disable Party Account Type Validation
# Reason: Front Desk users are unable to record payments because of permission issues 
# with Account Type validation. This validation prevents setting a Party for non-Receivable/Payable accounts.
def validate_account_party_type(self):
    pass

# Patch the original function in party.py
erpnext.accounts.party.validate_account_party_type = validate_account_party_type

# Patch the imported function in gl_entry.py
erpnext.accounts.doctype.gl_entry.gl_entry.validate_account_party_type = validate_account_party_type
