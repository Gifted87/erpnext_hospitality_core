# Copyright (c) 2026, Gift Braimah and contributors
# For license information, please see license.txt

"""
Composite Item Utilities

This module handles stock deduction for composite items (recipe-based items).
When a composite item is sold, ingredients are automatically consumed from stock.
"""

import frappe
from frappe import _
from frappe.utils import flt, now
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


def process_composite_items_in_invoice(doc, method=None):
	"""
	Process composite items in POS Invoice or Sales Invoice.
	Creates Material Consumption stock entries for ingredients.
	
	Args:
		doc: POS Invoice or Sales Invoice document
		method: Event method (on_submit, on_cancel)
	"""
	# Determine if this is a cancellation
	is_cancel = doc.docstatus == 2
	
	# Get composite items from invoice
	composite_items = []
	for item in doc.items:
		if frappe.db.get_value("Item", item.item_code, "is_composite_item"):
			composite_items.append(item)
	
	if not composite_items:
		return
	
	# Process each composite item
	for item in composite_items:
		try:
			if is_cancel:
				# Reverse the stock entry
				reverse_ingredient_consumption(doc, item)
			else:
				# Create consumption entry
				create_ingredient_consumption_entry(
					item_code=item.item_code,
					qty=item.qty,
					warehouse=item.warehouse,
					invoice_ref=doc.name,
					invoice_type=doc.doctype,
					posting_date=doc.posting_date,
					posting_time=doc.posting_time
				)
		except Exception as e:
			frappe.log_error(
				message=f"Error processing composite item {item.item_code}: {str(e)}",
				title="Composite Item Processing Error"
			)
			# Re-raise to prevent invoice submission if stock deduction fails
			frappe.throw(_("Failed to process composite item {0}. Error: {1}").format(
				item.item_code, str(e)
			))


def create_ingredient_consumption_entry(item_code, qty, warehouse, invoice_ref, 
										 invoice_type, posting_date=None, posting_time=None):
	"""
	Create Stock Entry for consuming ingredients based on BOM.
	
	Args:
		item_code: Composite item code
		qty: Quantity of composite item sold
		warehouse: Warehouse to deduct from
		invoice_ref: Reference to invoice for tracking
		invoice_type: Type of invoice (POS Invoice or Sales Invoice)
		posting_date: Date of posting
		posting_time: Time of posting
	
	Returns:
		Stock Entry document
	"""
	# Get the recipe (BOM)
	bom = get_active_bom(item_code)
	if not bom:
		frappe.throw(_("No active recipe found for item {0}").format(item_code))
	
	# Get ingredients from BOM
	ingredients = get_bom_ingredients(bom, qty)
	
	if not ingredients:
		frappe.throw(_("No ingredients found in recipe for {0}").format(item_code))
	
	# Validate stock availability
	validate_ingredient_availability(ingredients, warehouse)
	
	# Create Stock Entry
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.stock_entry_type = "Material Consumption for Manufacture"
	stock_entry.purpose = "Material Consumption for Manufacture"
	stock_entry.company = frappe.defaults.get_defaults().get("company")
	
	if posting_date:
		stock_entry.posting_date = posting_date
	if posting_time:
		stock_entry.posting_time = posting_time
	
	# Add custom fields for tracking
	stock_entry.custom_composite_item = item_code
	stock_entry.custom_source_invoice = invoice_ref
	stock_entry.custom_invoice_type = invoice_type
	
	# Add ingredients as items
	for ingredient in ingredients:
		stock_entry.append("items", {
			"item_code": ingredient["item_code"],
			"qty": ingredient["qty"],
			"s_warehouse": warehouse,
			"uom": ingredient["uom"],
			"stock_uom": ingredient["stock_uom"],
			"conversion_factor": ingredient.get("conversion_factor", 1)
		})
	
	# Save and submit
	stock_entry.insert(ignore_permissions=True)
	stock_entry.submit()
	
	return stock_entry


def reverse_ingredient_consumption(invoice_doc, item):
	"""
	Reverse stock entry when invoice is cancelled.
	
	Args:
		invoice_doc: Invoice document
		item: Item row from invoice
	"""
	# Find the stock entry created for this invoice and item
	stock_entries = frappe.get_all(
		"Stock Entry",
		filters={
			"custom_source_invoice": invoice_doc.name,
			"custom_composite_item": item.item_code,
			"docstatus": 1
		},
		pluck="name"
	)
	
	# Cancel all related stock entries
	for entry_name in stock_entries:
		try:
			stock_entry = frappe.get_doc("Stock Entry", entry_name)
			stock_entry.cancel()
		except Exception as e:
			frappe.log_error(
				message=f"Error cancelling stock entry {entry_name}: {str(e)}",
				title="Stock Entry Cancellation Error"
			)


def get_active_bom(item_code):
	"""
	Get the active BOM for a composite item.
	
	Args:
		item_code: Item code
		
	Returns:
		BOM name or None
	"""
	# Try to get from Item Recipe first
	recipe = frappe.db.get_value("Item Recipe", item_code, "bom")
	if recipe:
		return recipe
	
	# Fallback to default BOM from Item
	bom = frappe.db.get_value("Item", item_code, "default_bom")
	if bom:
		return bom
	
	# Find any active BOM for this item
	bom = frappe.db.get_value(
		"BOM",
		filters={"item": item_code, "is_active": 1, "docstatus": 1},
		fieldname="name",
		order_by="creation desc"
	)
	
	return bom


def get_bom_ingredients(bom_name, qty_multiplier):
	"""
	Get ingredients from BOM with quantities multiplied.
	
	Args:
		bom_name: BOM document name
		qty_multiplier: Quantity to multiply ingredient quantities by
		
	Returns:
		List of ingredient dicts
	"""
	bom = frappe.get_doc("BOM", bom_name)
	ingredients = []
	
	for item in bom.items:
		# Calculate required quantity based on BOM quantity
		qty_per_unit = flt(item.stock_qty) / flt(bom.quantity)
		required_qty = qty_per_unit * flt(qty_multiplier)
		
		ingredients.append({
			"item_code": item.item_code,
			"qty": required_qty,
			"uom": item.uom,
			"stock_uom": item.stock_uom,
			"conversion_factor": item.conversion_factor
		})
	
	return ingredients


def validate_ingredient_availability(ingredients, warehouse):
	"""
	Validate that sufficient ingredients exist before sale.
	
	Args:
		ingredients: List of ingredient dicts
		warehouse: Warehouse to check
		
	Raises:
		frappe.ValidationError if insufficient stock
	"""
	insufficient_items = []
	
	for ingredient in ingredients:
		available_qty = get_available_qty(ingredient["item_code"], warehouse)
		
		if available_qty < ingredient["qty"]:
			insufficient_items.append({
				"item": ingredient["item_code"],
				"required": ingredient["qty"],
				"available": available_qty
			})
	
	if insufficient_items:
		error_msg = _("Insufficient ingredients to make this item:") + "\n"
		for item_info in insufficient_items:
			error_msg += _("• {0}: Required {1}, Available {2}").format(
				item_info["item"],
				item_info["required"],
				item_info["available"]
			) + "\n"
		
		frappe.throw(error_msg, title=_("Insufficient Stock"))


def get_available_qty(item_code, warehouse):
	"""
	Get available quantity of an item in warehouse.
	
	Args:
		item_code: Item code
		warehouse: Warehouse name
		
	Returns:
		Float: Available quantity
	"""
	from erpnext.stock.utils import get_stock_balance
	
	return get_stock_balance(item_code, warehouse)


@frappe.whitelist()
def get_available_to_make(item_code, warehouse=None):
	"""
	Calculate how many units of composite item can be made
	based on available ingredients.
	
	Args:
		item_code: Composite item code
		warehouse: Optional warehouse filter
		
	Returns:
		Dict with quantity and details
	"""
	# Check if item is composite
	is_composite = frappe.db.get_value("Item", item_code, "is_composite_item")
	if not is_composite:
		return {"qty": 0, "message": "Item is not a composite item"}
	
	# Get BOM
	bom_name = get_active_bom(item_code)
	if not bom_name:
		return {"qty": 0, "message": "No active recipe found"}
	
	bom = frappe.get_doc("BOM", bom_name)
	
	# Calculate maximum quantity based on ingredients
	max_qty = None
	ingredient_details = []
	
	for item in bom.items:
		qty_per_unit = flt(item.stock_qty) / flt(bom.quantity)
		available = get_available_qty(item.item_code, warehouse)
		
		# Calculate how many units can be made with this ingredient
		if qty_per_unit > 0:
			can_make = available / qty_per_unit
		else:
			can_make = 0
		
		ingredient_details.append({
			"ingredient": item.item_code,
			"required_per_unit": qty_per_unit,
			"available": available,
			"can_make": int(can_make)
		})
		
		# Track the limiting ingredient
		if max_qty is None or can_make < max_qty:
			max_qty = can_make
	
	return {
		"qty": int(max_qty) if max_qty is not None else 0,
		"ingredients": ingredient_details,
		"message": "Success"
	}
