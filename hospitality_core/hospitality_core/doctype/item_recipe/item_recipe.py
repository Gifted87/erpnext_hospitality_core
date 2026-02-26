# Copyright (c) 2026, Gift Braimah and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ItemRecipe(Document):
	def validate(self):
		"""Validate recipe before saving"""
		self.validate_composite_item()
		self.validate_ingredients()
		self.calculate_stock_quantities()
	
	def validate_composite_item(self):
		"""Ensure the item is marked as composite"""
		if not frappe.db.get_value("Item", self.item, "is_composite_item"):
			frappe.throw(_("Item {0} must be marked as 'Composite Item' to create a recipe").format(self.item))
	
	def validate_ingredients(self):
		"""Validate ingredient items"""
		if not self.ingredients:
			frappe.throw(_("At least one ingredient is required"))
		
		# Check for duplicate ingredients
		ingredient_items = [d.ingredient_item for d in self.ingredients]
		if len(ingredient_items) != len(set(ingredient_items)):
			frappe.throw(_("Duplicate ingredients are not allowed"))
		
		# Check for circular reference (item cannot be its own ingredient)
		if self.item in ingredient_items:
			frappe.throw(_("Item {0} cannot be an ingredient of itself").format(self.item))
	
	def calculate_stock_quantities(self):
		"""Calculate stock quantities for ingredients"""
		for ingredient in self.ingredients:
			if not ingredient.ingredient_item:
				continue
			
			# Fetch stock UOM from item
			stock_uom = frappe.db.get_value("Item", ingredient.ingredient_item, "stock_uom")
			ingredient.stock_uom = stock_uom
			
			# Calculate stock quantity based on UOM conversion
			if ingredient.uom == stock_uom:
				ingredient.stock_qty = ingredient.qty
			else:
				# Get conversion factor
				conversion_factor = get_uom_conversion_factor(
					ingredient.ingredient_item,
					ingredient.uom,
					stock_uom
				)
				ingredient.stock_qty = flt(ingredient.qty) * flt(conversion_factor)
	
	def on_update(self):
		"""Create or update BOM after save"""
		self.sync_bom()
	
	def on_trash(self):
		"""Delete linked BOM when recipe is deleted"""
		if self.bom:
			try:
				bom_doc = frappe.get_doc("BOM", self.bom)
				if bom_doc.docstatus == 1:
					bom_doc.cancel()
				frappe.delete_doc("BOM", self.bom, force=1)
			except Exception as e:
				frappe.log_error(f"Error deleting BOM {self.bom}: {str(e)}")
	
	def sync_bom(self):
		"""Synchronize recipe with ERPNext BOM"""
		if self.bom:
			# Update existing BOM
			self.update_bom()
		else:
			# Create new BOM
			self.create_bom()
	
	def create_bom(self):
		"""Create a new BOM for this recipe"""
		bom = frappe.new_doc("BOM")
		bom.item = self.item
		bom.quantity = self.quantity
		bom.uom = self.uom
		bom.is_active = self.is_active
		bom.is_default = 1
		bom.company = frappe.defaults.get_defaults().get("company")
		
		# Add ingredients as BOM items
		for ingredient in self.ingredients:
			bom.append("items", {
				"item_code": ingredient.ingredient_item,
				"qty": ingredient.qty,
				"uom": ingredient.uom,
				"stock_qty": ingredient.stock_qty,
				"stock_uom": ingredient.stock_uom,
				"rate": frappe.db.get_value("Item", ingredient.ingredient_item, "valuation_rate") or 0
			})
		
		bom.insert(ignore_permissions=True)
		bom.submit()
		
		# Store BOM reference
		self.db_set("bom", bom.name, update_modified=False)
	
	def update_bom(self):
		"""Update existing BOM"""
		try:
			bom = frappe.get_doc("BOM", self.bom)
			
			# If it's submitted, we must cancel it.
			# If it's cancelled, we can't save it. In both cases, create a new one.
			if bom.docstatus > 0:
				if bom.docstatus == 1:
					bom.cancel()
				
				# Create a new version
				self.create_bom()
				return
			
			# If it's still in draft (docstatus 0), update it
			bom.quantity = self.quantity
			bom.uom = self.uom
			bom.is_active = self.is_active
			
			# Clear and re-add items
			bom.set("items", [])
			for ingredient in self.ingredients:
				bom.append("items", {
					"item_code": ingredient.ingredient_item,
					"qty": ingredient.qty,
					"uom": ingredient.uom,
					"stock_qty": ingredient.stock_qty,
					"stock_uom": ingredient.stock_uom,
					"rate": frappe.db.get_value("Item", ingredient.ingredient_item, "valuation_rate") or 0
				})
			
			bom.save(ignore_permissions=True)
			bom.submit()
			
		except Exception as e:
			frappe.log_error(f"Error updating BOM {self.bom}: {str(e)}")
			frappe.throw(_("Failed to update BOM. Please check error log."))


def get_uom_conversion_factor(item_code, from_uom, to_uom):
	"""Get UOM conversion factor"""
	if from_uom == to_uom:
		return 1.0
	
	# Check if conversion exists
	conversion = frappe.db.get_value(
		"UOM Conversion Detail",
		{"parent": item_code, "uom": from_uom},
		"conversion_factor"
	)
	
	if conversion:
		return flt(conversion)
	
	# Default to 1 if no conversion found
	return 1.0
