import frappe
import json
import os

def sync_hospitality_workspace():
	json_path = "/home/erpnext/frappe-bench/apps/hospitality_core/hospitality_core/hospitality_core/workspace/hospitality/hospitality.json"
	
	if not os.path.exists(json_path):
		print(f"Error: JSON file not found at {json_path}")
		return

	with open(json_path, "r") as f:
		ws_data = json.load(f)

	if frappe.db.exists("Workspace", "Hospitality"):
		doc = frappe.get_doc("Workspace", "Hospitality")
		
		# Update core fields
		doc.content = ws_data.get("content")
		
		# Use set() for child tables to properly handle dict to BaseDocument conversion
		doc.set("charts", ws_data.get("charts", []))
		doc.set("number_cards", ws_data.get("number_cards", []))
		doc.set("links", ws_data.get("links", []))
		doc.set("shortcuts", ws_data.get("shortcuts", []))
		
		# Ensure it's public and correctly labeled
		doc.public = 1
		doc.is_standard = 1
		doc.module = "Hospitality Core"
		
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		print("✔ Workspace 'Hospitality' updated successfully in Database.")
	else:
		print("Error: Workspace 'Hospitality' not found in Database.")

if __name__ == "__main__":
	sync_hospitality_workspace()
