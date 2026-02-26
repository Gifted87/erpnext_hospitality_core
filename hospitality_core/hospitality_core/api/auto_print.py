"""
Automatic Receipt Printing Module

This module provides settings for client-side automatic printing of receipts.
The actual printing happens on the client browser, not the server.
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_print_settings():
	"""
	Get automatic printing settings for client-side use.
	Returns settings if auto-print is enabled, otherwise returns disabled status.
	
	Returns:
		dict: Settings dictionary with enabled, copies, and print_format
	"""
	try:
		settings = frappe.get_single("Hospitality Accounting Settings")
		
		return {
			"enabled": settings.enable_auto_print or False,
			"copies": settings.print_copies or 3,
			"print_format": settings.receipt_print_format or "Standard"
		}
	except Exception as e:
		frappe.log_error(
			title=_("Auto Print: Settings Error"),
			message=f"Failed to get print settings: {str(e)}"
		)
		return {
			"enabled": False,
			"copies": 3,
			"print_format": "Standard"
		}

