# Hospitality Financial System: Comprehensive Testing Guide

This guide walks you through the testing of the entire Hospitality Financial System, from initial setup to consolidated performance reporting.

## 1. Dashboard Navigation
- **Action**: From the Frappe Desk, navigate to the **Hospitality** Workspace.
- **Verification**: Ensure you see the new links under **Accounting & Billing** (`Hospitality Expense`, `Expense Category`) and **Financial Reports** (`Gross Revenue Report`, `Hospitality Expense Report`).

---

## 2. Managing Hierarchical Categories
- **Path**: `Hospitality Workspace > Expense Category`
- **Action**: 
    1. Create a new category called `Energy`. Mark it as a **Group**.
    2. Create another category called `Solar Maintenance`. Set its **Parent Category** to `Energy`.
- **Verification**: Open the `Energy` category and ensure it shows its children. Check that you can filter reports by the top-level `Energy` group.

---

## 3. The Expense Lifecycle (Workflow & Accounting)
- **Path**: `Hospitality Workspace > Hospitality Expense`
- **Scenario**: Recording a repair for a room.
- **Action**:
    1. Click **New**.
    2. Select an **Expense Category** (e.g., `Electrical`).
    3. Enter a **Net Amount** (e.g., `10000`).
    4. Link a **Supplier** and a **Hotel Reception**.
    5. **Taxes**: In the Taxes table, add `VAT - EHH` at `7.5%`.
    6. **Save**.
- **Workflow Action**:
    1. Click the status button at the top right: **Submit for Approval**.
    2. Click it again: **Approve**.
- **Verification**:
    1. The document should now be **Approved** and **Submitted** (DocStatus 1).
    2. Click **View > Ledger**. You should see 3 entries:
        - **Debit** (Expense Account): 10,000
        - **Debit** (VAT Account): 750
        - **Credit** (Cash/Bank): 10,750

---

## 4. Maintenance Cost Roll-up
- **Path**: `Hospitality Workspace > Maintenance Requests`
- **Action**: 
    1. Open a Maintenance Request.
    2. Look for the **Total Expenses** field (read-only).
- **Verification**: The field should automatically show the sum of all **Approved** expenses linked to this request.

---

## 5. High-Level Performance (Gross Revenue Report)
- **Path**: `Hospitality Workspace > Gross Revenue Report`
- **Action**:
    1. Set the date range (e.g., select the current month).
    2. Change the **Group By** filter (Room, Room Type, or Reception).
- **Verification**: 
    - Check that **Revenue** matches your folio charges.
    - Check that **Buying Amount (Expenses)** matches the expenses logged for those entities.
    - Verify the **Gross Profit %** provides a realistic look at your margins.

---

## 6. Granular Auditor View (Hospitality Expense Report)
- **Path**: `Hospitality Workspace > Hospitality Expense Report`
- **Action**:
    1. Filter by **Approval State** (Approved).
    2. Filter by **Supplier**.
- **Verification**: Review the distinct columns for **Net Amount**, **Total Tax**, and **Grand Total**. This is your final audit trail for every Naira spent.

---

### Need Help?
If any of these values seem incorrect, ensure that the **Expense Category** has a `Default Expense Account` linked and that the **Workflow** is in the `Approved` state.
