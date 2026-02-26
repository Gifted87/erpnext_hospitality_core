# Auto-Print Troubleshooting Guide

## Issue: Automatic printing not working after enabling in settings

### Solution Steps:

1. **Restart the bench** (CRITICAL - code changes won't take effect until restart)
   ```bash
   # Navigate to bench directory
   cd /home/erpnext/frappe-bench
   
   # Restart all bench processes
   bench restart
   ```

2. **Verify the settings are enabled**
   - Go to: Hospitality Accounting Settings
   - Confirm "Enable Automatic Receipt Printing" is checked
   - Note the "Number of Copies to Print" value

3. **Check if your system has a default printer**
   ```bash
   # Check default printer
   lpstat -d
   
   # If no default printer, set one:
   lpoptions -d <printer-name>
   
   # Test print
   echo "Test" | lp
   ```

4. **Submit a new POS Invoice** (after bench restart)
   - Create and submit a new POS Invoice
   - Check if print jobs appear

5. **Check for errors**
   - Go to: Error Log list
   - Filter by: "Auto Print" in the error field
   - Review any errors that appear

6. **Check the print queue**
   ```bash
   # View print queue
   lpstat -o
   
   # Or check system logs
   sudo journalctl -u cups -f
   ```

### Common Issues:

**Issue**: "No module named 'hospitality_core.hospitality_core.api.auto_print'"
**Solution**: Bench wasn't restarted. Run `bench restart`

**Issue**: "No default printer"
**Solution**: Set default printer with `lpoptions -d <printer-name>`

**Issue**: Print jobs queued but not printing
**Solution**: Check printer connection and CUPS service status

**Issue**: PDF generation error
**Solution**: Check if the print format exists and is valid

### Testing Script

Run this in bench console to test manually:
```python
bench console

# In the console:
from hospitality_core.hospitality_core.api.auto_print import auto_print_pos_invoice
import frappe

# Get a recent POS Invoice
inv = frappe.get_doc("POS Invoice", "YOUR-INVOICE-NAME")

# Manually trigger auto print
auto_print_pos_invoice(inv, "on_submit")
```
