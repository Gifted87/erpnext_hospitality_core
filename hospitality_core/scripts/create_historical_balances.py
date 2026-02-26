import frappe
from frappe.utils import flt, nowdate, now_datetime
from frappe.model.naming import make_autoname

DATA = [
    {"name": "OKPUNU THEOPHILES ODION", "amount": 25000.00},
    {"name": "OLADAPO BRIDGET", "amount": 1354620.00},
    {"name": "OLUWADARE FEMI", "amount": 100.00},
    {"name": "OMORAGBON JACKSON", "amount": 100.00},
    {"name": "OMOREGBEE FRANK", "amount": 25000.00},
    {"name": "OMOROGOWA EOHUNMWUNGIE", "amount": 23000.00},
    {"name": "ONAVWIE EMMANUEL", "amount": 30000.00},
    {"name": "Orasanya Pst. Jeff", "amount": 70000.00},
    {"name": "OSAGHAE EHIZE", "amount": 100.00},
    {"name": "Osagiede Samson", "amount": 25000.00},
    {"name": "OSAHON SAMUEL (JECINTTA GUEST)", "amount": 250000.00},
    {"name": "OSAIGBOVO ERHARUYI", "amount": 40000.00},
    {"name": "OSARO RAYMOND ASEMOTA", "amount": 100000.00},
    {"name": "OSAYIEDE DESTINY", "amount": 25000.00},
    {"name": "OSAZUWA JERRY", "amount": 600.00},
    {"name": "osunde anthony", "amount": 21200.00},
    {"name": "osunde ehi", "amount": 10000.00},
    {"name": "OSUNDE LILIAN", "amount": 70000.00},
    {"name": "OZEBBA FELIX", "amount": 80000.00},
    {"name": "PABLO TREASURE", "amount": 25000.00},
    {"name": "PATENICE PAUL UMOGBAI", "amount": 96000.00},
    {"name": "PHILOMENA MOORE", "amount": 10000.00},
    {"name": "PIERPAOLO TOMMASINI", "amount": 200.00},
    {"name": "PRECIOUS DAVID", "amount": 70000.00},
    {"name": "PREST ISAAC", "amount": 35000.00},
    {"name": "RIAKPOYERIN CLEMENT", "amount": 105000.00},
    {"name": "S LEADER ARENA", "amount": 35000.00},
    {"name": "SAINT PATRICK", "amount": 100.00},
    {"name": "SANDRA EMORON", "amount": 50000.00},
    {"name": "SARUMI ADEBAYO", "amount": 35000.00},
    {"name": "Solomon Tope", "amount": 700.00},
    {"name": "ST MOSES EROMOSELE", "amount": 10000.00},
    {"name": "TOKUNBO DARAMOLA", "amount": 35000.00},
    {"name": "udenigue nwamaka", "amount": 100.00},
    {"name": "UFUOMA YINKORE (MADAM JOCINTA GUEST)", "amount": 25000.00},
    {"name": "UMAR SANI", "amount": 24400.00},
    {"name": "UNILFUN ODIGIE", "amount": 5600.00},
    {"name": "USMAN AHMED (CUSTOMS COMPTROLLER)", "amount": 25000.00},
    {"name": "UWAILA ABIES", "amount": 43000.00},
    {"name": "UYI IDUOZEE", "amount": 20000.00},
    {"name": "VALETINE JOSHUA", "amount": 5000.00},
    {"name": "VEGO (LYON) PEDO", "amount": 300.00},
    {"name": "VICTOR UADIALE", "amount": 20000.00},
    {"name": "WALE OKE (N.C.G.C)", "amount": 22000.00},
    {"name": "WILLIAM PHILEMON", "amount": 50.00},
    {"name": "YUKIO IKEDA 2", "amount": 35242.25},
    {"name": "YUKIO IKEDA 3", "amount": 35242.25},
    {"name": "zanny zena", "amount": 30000.00},
    {"name": "ZOFMON INVESTMENT", "amount": 4500.00},
]

def run():
    print("Starting Historical Ledger Creation (Batch 3)...")
    created_count = 0
    
    for item in DATA:
        name = item['name']
        amount = item['amount']
        
        # 1. Ensure Guest Exists
        guest_id = frappe.db.get_value("Guest", {"full_name": name}, "name")
        if not guest_id:
            guest = frappe.get_doc({
                "doctype": "Guest",
                "full_name": name,
                "guest_type": "Regular"
            })
            guest.insert(ignore_permissions=True)
            guest_id = guest.name
            print(f"Created Guest: {name}")

        # 2. Check for existing ledger entry to avoid duplicates (loose check by guest and amount)
        if frappe.db.exists("Guest Balance Ledger", {"guest": guest_id, "amount": amount, "status": "Available"}):
            print(f"Skipping {name}: Ledger entry with amount {amount} already exists.")
            continue

        # 3. Create a Dummy Folio (Historical)
        folio = frappe.get_doc({
            "doctype": "Guest Folio",
            "guest": guest_id,
            "status": "Closed",
            "open_date": "2026-01-01",
            "close_date": "2026-01-01",
            "outstanding_balance": -1 * amount, # Credit balance
            "total_payments": amount,
            "total_charges": 0.0
        })
        folio.naming_series = "FOLIO-.#####"
        folio.insert(ignore_permissions=True)
        print(f"Created Folio {folio.name} for {name}")

        # 4. Create Ledger Entry
        ledger_entry = frappe.get_doc({
            "doctype": "Guest Balance Ledger",
            "guest": guest_id,
            "folio": folio.name,
            "amount": amount,
            "status": "Available",
            "date": "2026-01-01"
        })
        ledger_entry.insert(ignore_permissions=True)
        print(f"Created Ledger Entry for {name}: {amount}")
        
        created_count += 1

    frappe.db.commit()
    print(f"Total entries created in Batch 3: {created_count}")

if __name__ == "__main__":
    run()
