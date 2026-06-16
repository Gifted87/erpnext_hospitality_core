import frappe

def create_child_table(doctype_name, fields):
    if not frappe.db.exists("DocType", doctype_name):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": doctype_name,
            "module": "Hospitality Core",
            "custom": 1,
            "istable": 1,
            "fields": fields
        })
        doc.insert(ignore_permissions=True)
        print(f"Created Child Table: {doctype_name}")
    else:
        print(f"DocType already exists: {doctype_name}")

def create_main_doctype():
    doctype_name = "End of Day Sales Generator"
    if not frappe.db.exists("DocType", doctype_name):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": doctype_name,
            "module": "Hospitality Core",
            "custom": 1,
            "issingle": 0,
            "autoname": "format:EOD-REPORT-{YYYY}-{MM}-{####}",
            "fields": [
                {"fieldname": "company", "fieldtype": "Link", "options": "Company", "label": "Company", "reqd": 1, "in_list_view": 1},
                {"fieldname": "from_date_time", "fieldtype": "Datetime", "label": "From Date & Time", "reqd": 1, "in_list_view": 1},
                {"fieldname": "to_date_time", "fieldtype": "Datetime", "label": "To Date & Time", "reqd": 1, "in_list_view": 1},
                {"fieldname": "pos_entry_status", "fieldtype": "Select", "label": "POS Entry Status", "options": "Submitted\nDraft", "default": "Submitted", "reqd": 1},
                {"fieldname": "pos_profiles", "fieldtype": "Table MultiSelect", "label": "POS Profiles", "options": "EOD POS Profile"},
                
                {"fieldname": "section_break_summary", "fieldtype": "Section Break", "label": "Summary"},
                {"fieldname": "total_expected_amount", "fieldtype": "Currency", "label": "Total Expected Amount", "read_only": 1},
                {"fieldname": "total_actual_amount", "fieldtype": "Currency", "label": "Total Actual Amount", "read_only": 1},
                {"fieldname": "total_difference", "fieldtype": "Currency", "label": "Total Difference", "read_only": 1},
                {"fieldname": "column_break_kpi", "fieldtype": "Column Break"},
                {"fieldname": "net_sales", "fieldtype": "Currency", "label": "Net Sales", "read_only": 1},
                {"fieldname": "total_taxes", "fieldtype": "Currency", "label": "Total Taxes", "read_only": 1},
                {"fieldname": "total_transactions", "fieldtype": "Int", "label": "Total Transactions", "read_only": 1},
                
                {"fieldname": "section_break_item", "fieldtype": "Section Break", "label": "Item Sales"},
                {"fieldname": "eod_item_sales", "fieldtype": "Table", "label": "Item Sales", "options": "EOD Item Sales"},
                
                {"fieldname": "section_break_group", "fieldtype": "Section Break", "label": "Item Group Sales"},
                {"fieldname": "eod_item_group_sales", "fieldtype": "Table", "label": "Item Group Sales", "options": "EOD Item Group Sales"},
                
                {"fieldname": "section_break_payment", "fieldtype": "Section Break", "label": "Payment Mode Summary"},
                {"fieldname": "eod_payment_summary", "fieldtype": "Table", "label": "Payment Summary", "options": "EOD Payment Summary"},
                
                {"fieldname": "section_break_expenses", "fieldtype": "Section Break", "label": "Expense Breakdown"},
                {"fieldname": "eod_expense_breakdown", "fieldtype": "Table", "label": "Expense Breakdown", "options": "EOD Expense Breakdown"},
                
                {"fieldname": "section_break_discrepancies", "fieldtype": "Section Break", "label": "Discrepancies"},
                {"fieldname": "eod_discrepancies", "fieldtype": "Table", "label": "Discrepancies", "options": "EOD Discrepancies"},
            ]
        })
        doc.insert(ignore_permissions=True)
        print(f"Created DocType: {doctype_name}")
        
    else:
        print(f"DocType already exists: {doctype_name}")

def execute():
    # 0. POS Profile Link Table
    create_child_table("EOD POS Profile", [
        {"fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "label": "POS Profile", "in_list_view": 1},
    ])
    
    # 1. EOD Item Sales
    create_child_table("EOD Item Sales", [
        {"fieldname": "pos_profile", "fieldtype": "Data", "label": "POS Profile", "in_list_view": 1},
        {"fieldname": "item_code", "fieldtype": "Data", "label": "Item Code", "in_list_view": 1},
        {"fieldname": "item_name", "fieldtype": "Data", "label": "Item Name", "in_list_view": 1},
        {"fieldname": "qty_sold", "fieldtype": "Float", "label": "Qty Sold", "in_list_view": 1},
        {"fieldname": "amount", "fieldtype": "Currency", "label": "Amount", "in_list_view": 1},
    ])
    
    # 2. EOD Item Group Sales
    create_child_table("EOD Item Group Sales", [
        {"fieldname": "item_group", "fieldtype": "Data", "label": "Item Group", "in_list_view": 1},
        {"fieldname": "qty_sold", "fieldtype": "Float", "label": "Qty Sold", "in_list_view": 1},
        {"fieldname": "amount", "fieldtype": "Currency", "label": "Amount", "in_list_view": 1},
    ])
    
    # 3. EOD Payment Summary
    create_child_table("EOD Payment Summary", [
        {"fieldname": "payment_mode", "fieldtype": "Data", "label": "Payment Mode", "in_list_view": 1},
        {"fieldname": "expected_amount", "fieldtype": "Currency", "label": "Expected Amount", "in_list_view": 1},
        {"fieldname": "actual_amount", "fieldtype": "Currency", "label": "Actual Amount", "in_list_view": 1},
        {"fieldname": "difference", "fieldtype": "Currency", "label": "Difference", "in_list_view": 1},
    ])
    
    # 4. EOD Expense Breakdown
    create_child_table("EOD Expense Breakdown", [
        {"fieldname": "expense_account", "fieldtype": "Data", "label": "Expense Account", "in_list_view": 1},
        {"fieldname": "amount", "fieldtype": "Currency", "label": "Amount", "in_list_view": 1},
    ])
    
    # 5. EOD Discrepancies
    create_child_table("EOD Discrepancies", [
        {"fieldname": "pos_closing_entry", "fieldtype": "Data", "label": "POS Closing Entry", "in_list_view": 1},
        {"fieldname": "pos_profile", "fieldtype": "Data", "label": "POS Profile", "in_list_view": 1},
        {"fieldname": "difference", "fieldtype": "Currency", "label": "Difference", "in_list_view": 1},
    ])
    
    # Main DocType
    create_main_doctype()
    
    frappe.db.commit()
