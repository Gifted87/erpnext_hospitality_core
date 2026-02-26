
import frappe
def check():
    meta = frappe.get_meta('Workspace Link')
    print("Fields in Workspace Link:")
    for f in meta.fields:
        print(f"- {f.fieldname} ({f.fieldtype})")
    
    # Also check if 'URL' is in options of 'link_type'
    for f in meta.fields:
        if f.fieldname == 'link_type':
            print(f"link_type options: {f.options}")

if __name__ == "__main__":
    check()
