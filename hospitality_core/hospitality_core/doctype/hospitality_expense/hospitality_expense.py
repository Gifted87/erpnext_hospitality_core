import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class HospitalityExpense(Document):
	def validate(self):
		self.set_account_details()
		self.calculate_taxes()
		self.calculate_totals()
		
	def on_submit(self):
		from hospitality_core.hospitality_core.api.accounting import create_expense_gl_entries
		create_expense_gl_entries(self)
		self.update_maintenance_request()
		
	def on_cancel(self):
		from hospitality_core.hospitality_core.api.accounting import create_expense_gl_entries
		create_expense_gl_entries(self, cancel=1)
		self.update_maintenance_request()

	def update_maintenance_request(self):
		if self.maintenance_request:
			m_req = frappe.get_doc("Hotel Maintenance Request", self.maintenance_request)
			m_req.recalculate_total_expenses()
		
	def set_account_details(self):
		if self.expense_category:
			self.expense_account = frappe.db.get_value("Expense Category", self.expense_category, "default_expense_account")
			
		if self.paid_via and not self.payment_account:
			# Try to fetch default account from Mode of Payment
			company = self.company or frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
			account = frappe.db.get_value("Mode of Payment Account", {"parent": self.paid_via, "company": company}, "default_account")
			if account:
				self.payment_account = account
				
		if not self.cost_center:
			settings = frappe.get_single("Hospitality Accounting Settings")
			if settings.cost_center:
				self.cost_center = settings.cost_center

	def calculate_taxes(self):
		self.total_taxes = 0
		for tax in self.get("taxes"):
			tax.tax_amount = flt(self.amount) * flt(tax.rate) / 100.0
			tax.total = flt(self.amount) + tax.tax_amount
			self.total_taxes += tax.tax_amount

	def calculate_totals(self):
		self.grand_total = flt(self.amount) + flt(self.total_taxes)
