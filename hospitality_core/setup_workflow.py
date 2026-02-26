import frappe

def setup_workflow():
    # 1. Create Workflow States
    states = ["Draft", "Pending Approval", "Approved", "Rejected"]
    for state in states:
        if not frappe.db.exists("Workflow State", state):
            frappe.get_doc({
                "doctype": "Workflow State",
                "workflow_state_name": state,
                "style": "Primary" if state == "Approved" else "Warning" if state == "Rejected" else ""
            }).insert(ignore_permissions=True)
            print(f"Created Workflow State: {state}")

    # 2. Create Workflow Action Masters
    actions = ["Submit for Approval", "Approve", "Reject"]
    for action in actions:
        if not frappe.db.exists("Workflow Action Master", action):
            frappe.get_doc({
                "doctype": "Workflow Action Master",
                "workflow_action_name": action
            }).insert(ignore_permissions=True)
            print(f"Created Workflow Action Master: {action}")

    # 3. Create Workflow
    if frappe.db.exists("Workflow", "Hospitality Expense Approval"):
        frappe.db.delete("Workflow", "Hospitality Expense Approval")
    
    workflow = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": "Hospitality Expense Approval",
        "document_type": "Hospitality Expense",
        "workflow_state_field": "workflow_state",
        "is_active": 1,
        "override_status": 1,
        "states": [
            {"state": "Draft", "allow_edit": "Hospitality User", "doc_status": 0},
            {"state": "Pending Approval", "allow_edit": "Hospitality Manager", "doc_status": 0},
            {"state": "Approved", "allow_edit": "Hospitality Manager", "doc_status": 1},
            {"state": "Rejected", "allow_edit": "Hospitality Manager", "doc_status": 2}
        ],
        "transitions": [
            {"state": "Draft", "action": "Submit for Approval", "next_state": "Pending Approval", "allowed": "Hospitality User"},
            {"state": "Pending Approval", "action": "Approve", "next_state": "Approved", "allowed": "Hospitality Manager"},
            {"state": "Pending Approval", "action": "Reject", "next_state": "Rejected", "allowed": "Hospitality Manager"}
        ]
    })
    workflow.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Workflow 'Hospitality Expense Approval' registered successfully.")

if __name__ == "__main__":
    setup_workflow()
