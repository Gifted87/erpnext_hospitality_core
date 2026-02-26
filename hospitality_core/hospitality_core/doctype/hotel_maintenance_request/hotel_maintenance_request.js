frappe.ui.form.on('Hotel Maintenance Request', {
    refresh: function (frm) {
        if (frm.doc.status !== 'Cancelled') {
            frm.add_custom_button(__('Log Expense'), function () {
                frappe.model.with_doctype('Hospitality Expense', function () {
                    let expense = frappe.model.get_new_doc('Hospitality Expense');
                    expense.maintenance_request = frm.doc.name;
                    expense.description = __('Maintenance for Room {0}: {1}', [frm.doc.room, frm.doc.description]);
                    expense.expense_category = 'Maintenance'; // Default if exists
                    frappe.set_route('Form', 'Hospitality Expense', expense.name);
                });
            });
        }
    }
});
