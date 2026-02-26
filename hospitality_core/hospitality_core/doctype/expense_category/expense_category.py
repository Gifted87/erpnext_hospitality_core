import frappe
from frappe.model.document import Document

class ExpenseCategory(Document):
	def validate(self):
		if not self.is_group and not self.default_expense_account:
			frappe.throw(_("Default Expense Account is mandatory for non-group categories."))
