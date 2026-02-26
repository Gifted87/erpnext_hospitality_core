# Copyright (c) 2026, Gift Braimah and contributors
# For license information, please see license.txt

"""
Setup script for composite item functionality - to be run via bench console.
Adds custom fields to Item DocType and creates necessary custom fields for Stock Entry.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup_composite_item_fields():
	"""Create custom fields for composite item functionality"""
	
	custom_fields = {
		"Item": [
			{
				"fieldname": "is_composite_item",
				"label": "Is Composite Item",
				"fieldtype": "Check",
				"insert_after": "is_stock_item",
				"description": "Enable this for recipe-based items (e.g., dishes made from ingredients)",
				"depends_on": "eval:doc.is_stock_item==0",
				"module": "Hospitality Core"
			}
		],
		"Stock Entry": [
			{
				"fieldname": "custom_composite_item",
				"label": "Composite Item",
				"fieldtype": "Link",
				"options": "Item",
				"insert_after": "purpose",
				"read_only": 1,
				"hidden": 1,
				"module": "Hospitality Core"
			},
			{
				"fieldname": "custom_source_invoice",
				"label": "Source Invoice",
				"fieldtype": "Data",
				"insert_after": "custom_composite_item",
				"read_only": 1,
				"hidden": 1,
				"module": "Hospitality Core"
			},
			{
				"fieldname": "custom_invoice_type",
				"label": "Invoice Type",
				"fieldtype": "Data",
				"insert_after": "custom_source_invoice",
				"read_only": 1,
				"hidden": 1,
				"module": "Hospitality Core"
			}
		]
	}
	
	create_custom_fields(custom_fields, update=True)
	frappe.db.commit()
	
	print("✓ Custom fields created successfully")
