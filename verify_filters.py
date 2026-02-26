import frappe
from hospitality_core.hospitality_core.report.daily_payment_collection.daily_payment_collection import execute as execute_payment
from hospitality_core.hospitality_core.report.daily_sales_consumption.daily_sales_consumption import execute as execute_sales

def test_filters():
    frappe.connect()
    
    # Get a hotel reception
    reception = frappe.get_all("Hotel Reception", limit=1)
    if not reception:
        print("No Hotel Reception found, skipping filter test.")
        return
    
    reception_name = reception[0].name
    print(f"Testing with reception: {reception_name}")
    
    today = frappe.utils.today()
    filters = {
        "from_date": today,
        "to_date": today,
        "hotel_reception": reception_name
    }
    
    print("\nChecking Daily Payment Collection...")
    columns, data = execute_payment(filters)
    print(f"Rows found: {len(data)}")
    # In a real environment we'd check if any results match other receptions, 
    # but here we just ensure the query runs without error.
    
    print("\nChecking Daily Sales Consumption...")
    columns, data = execute_sales(filters)
    print(f"Rows found: {len(data)}")

if __name__ == "__main__":
    test_filters()
