import frappe

def execute():
    # Set default print format for Payment Entry
    frappe.make_property_setter({
        'doctype': 'Payment Entry',
        'doctype_or_field': 'DocType',
        'property': 'default_print_format',
        'value': 'Payment Receipt Classic',
        'property_type': 'Data'
    })
    
    # Set default print format for Guest Folio
    frappe.make_property_setter({
        'doctype': 'Guest Folio',
        'doctype_or_field': 'DocType',
        'property': 'default_print_format',
        'value': 'Guest Folio Classic',
        'property_type': 'Data'
    })
    
    frappe.db.commit()
    print("Default print formats successfully set via Property Setter.")
