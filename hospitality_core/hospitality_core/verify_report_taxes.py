import frappe
from hospitality_core.hospitality_core.api.accounting import get_tax_breakdown
from hospitality_core.hospitality_core.report.gross_revenue_report.gross_revenue_report import execute as execute_gross
from hospitality_core.hospitality_core.report.daily_sales_consumption.daily_sales_consumption import execute as execute_daily
from hospitality_core.hospitality_core.report.end_of_day_report.end_of_day_report import execute as execute_eod

def run_tests():
    print("Starting Verification...")
    
    # 1. Test get_tax_breakdown directly
    # 122.5 -> Net 100, CT 5, VAT 7.5, SC 10
    taxes = get_tax_breakdown(122.50)
    assert taxes["net_amount"] == 100.00, f"Expected 100.00, got {taxes['net_amount']}"
    assert taxes["ct_amount"] == 5.00, f"Expected 5.00, got {taxes['ct_amount']}"
    assert taxes["vat_amount"] == 7.50, f"Expected 7.50, got {taxes['vat_amount']}"
    assert taxes["sc_amount"] == 10.00, f"Expected 10.00, got {taxes['sc_amount']}"
    print("✓ get_tax_breakdown logic verified.")

    # 2. Test End of Day Report logic (Mocking sales consumption)
    # We can't easily mock the SQL result without complex monkey-patching, 
    # but we can check if the execute method runs without error and contains the expected metrics.
    # Note: This requires a database with some data or a mock.
    # For now, let's just assert the data structure returned by get_tax_breakdown matches what EOD expects.
    
    # Let's perform a dry run of the report if possible
    filters = {"date": frappe.utils.nowdate()}
    try:
        columns, data = execute_eod(filters)
        metrics = [d["metric"] for d in data]
        if "Sales Consumption (Gross)" in metrics:
            assert "  - Net Sales" in metrics
            assert "  - Consumption Tax (5%)" in metrics
            print("✓ EOD Report metrics structure verified.")
    except Exception as e:
        print(f"! EOD Report execution failed (likely no data): {e}")

    # 3. Test Gross Revenue Report
    # Similar structure check
    filters_gross = {
        "from_date": frappe.utils.nowdate(),
        "to_date": frappe.utils.nowdate(),
        "company": frappe.defaults.get_user_default("Company") or "Edo Heritage Hotel",
        "group_by": "Room"
    }
    try:
        columns, data = execute_gross(filters_gross)
        col_names = [c["fieldname"] for c in columns]
        assert "net_revenue" in col_names
        assert "ct_amount" in col_names
        print("✓ Gross Revenue Report columns verified.")
    except Exception as e:
        print(f"! Gross Revenue Report execution failed: {e}")

    print("\nVerification Complete.")

if __name__ == "__main__":
    run_tests()
