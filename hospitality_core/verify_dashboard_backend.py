import frappe
from hospitality_core.hospitality_core.dashboard_data import get_today_occupancy

def verify_whitelist():
	print("--- Backend Whitelist Verification ---")
	
	# Check the function itself
	print(f"Function 'get_today_occupancy' whitelisted: {hasattr(get_today_occupancy, 'whitelisted')}")
	
	# Check Number Cards
	cards = ["Today's Occupancy %", "Today's Revenue", "Today's Expenses"]
	for card_name in cards:
		if frappe.db.exists("Number Card", card_name):
			card = frappe.get_doc("Number Card", card_name)
			print(f"Card: {card_name}")
			print(f"  - Method: {card.method}")
			print(f"  - Type: {card.type}")
			
			# Check if method is resolveable and whitelisted
			try:
				parts = card.method.split(".")
				module_path = ".".join(parts[:-1])
				fn_name = parts[-1]
				module = __import__(module_path, fromlist=[fn_name])
				fn = getattr(module, fn_name)
				print(f"  - Resolved Function Whitelisted: {hasattr(fn, 'whitelisted')}")
			except Exception as e:
				print(f"  - Error resolving method: {e}")
		else:
			print(f"Card: {card_name} NOT FOUND")

if __name__ == "__main__":
	verify_whitelist()
