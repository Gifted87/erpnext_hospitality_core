frappe.ui.form.on('Guest Balance Ledger', {
    refresh: function (frm) {
        let can_issue_refund = true;

        if (frm.doc.status === 'Available' && frm.doc.amount > 0 && can_issue_refund) {
            frm.add_custom_button(__('Issue Refund'), function () {
                issue_ledger_refund_dialog(frm);
            }, 'Actions');
        }
    }
});

function issue_ledger_refund_dialog(frm) {
    var d = new frappe.ui.Dialog({
        title: __('Issue Refund'),
        fields: [
            {
                label: __('Guest'),
                fieldname: 'guest_display',
                fieldtype: 'Data',
                read_only: 1,
                default: frm.doc.guest || ''
            },
            {
                label: __('Available Credit'),
                fieldname: 'credit_display',
                fieldtype: 'Currency',
                read_only: 1,
                default: frm.doc.amount
            },
            { fieldtype: 'Section Break' },
            {
                label: __('Refund Amount'),
                fieldname: 'amount',
                fieldtype: 'Currency',
                reqd: 1,
                default: frm.doc.amount,
                description: __('Enter amount to refund to customer')
            },
            {
                label: __('Hotel Reception'),
                fieldname: 'hotel_reception',
                fieldtype: 'Link',
                options: 'Hotel Reception',
                reqd: 1,
                description: __('Select the reception issuing the refund')
            }
        ],
        primary_action_label: __('Process Refund'),
        primary_action: function (values) {
            if (values.amount <= 0) {
                frappe.msgprint(__('Amount must be greater than zero.'));
                return;
            }
            if (values.amount > frm.doc.amount + 0.01) {
                frappe.msgprint(__('Refund amount cannot exceed available credit.'));
                return;
            }
            d.hide();
            frappe.dom.freeze(__('Processing refund...'));

            frappe.call({
                method: 'hospitality_core.hospitality_core.api.payment_bridge.issue_ledger_refund',
                args: {
                    ledger_name:      frm.doc.name,
                    amount:           values.amount,
                    hotel_reception:  values.hotel_reception
                },
                callback: function (r) {
                    frappe.dom.unfreeze();
                    if (!r.exc && r.message) {
                        frappe.show_alert({
                            message: __('Refund {0} recorded successfully', [r.message]),
                            indicator: 'green'
                        }, 6);
                        frm.reload_doc();
                        // Open the newly created Payment Entry document
                        frappe.set_route('Form', 'Payment Entry', r.message);
                    }
                },
                error: function () {
                    frappe.dom.unfreeze();
                }
            });
        }
    });
    d.show();
}
