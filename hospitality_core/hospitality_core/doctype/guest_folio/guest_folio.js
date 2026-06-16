frappe.ui.form.on('Guest Folio', {
    refresh: function (frm) {
        // Only set read-only if formally closed
        if (frm.doc.status === 'Closed' || frm.doc.status === 'Cancelled') {
            frm.set_read_only();
        }

        // Lock Is Company Master Folio and Company after the first save
        // (frm.is_new() returns true only before the document has ever been saved)
        const is_saved = !frm.is_new();
        frm.set_df_property('is_company_master', 'read_only', is_saved ? 1 : 0);
        frm.set_df_property('company', 'read_only', is_saved ? 1 : 0);

        // Button: Record Payment (Guest Folio only)
        if (!frm.doc.is_company_master && (frm.doc.status === 'Open' || frm.doc.status === 'Closed')) {
            frm.add_custom_button(__('Record Payment'), function () {
                make_payment_entry(frm);
            }, 'Actions');
        }

        // Button: Issue Refund
        let can_issue_refund = true;

        if (!frm.doc.is_company_master && (frm.doc.status === 'Open' || frm.doc.status === 'Closed') && frm.doc.outstanding_balance < -0.01 && can_issue_refund) {
            frm.add_custom_button(__('Issue Refund'), function () {
                issue_refund_dialog(frm);
            }, 'Actions');
        }

        // Company Folio Buttons
        if (frm.doc.is_company_master && frm.doc.status === 'Open') {
            // Record Payment to Company: offsets city ledger (credit side)
            frm.add_custom_button(__('Record Payment to Company'), function () {
                make_company_payment_entry(frm);
            }, 'Actions');

            // Record Transaction: manually post a debit to the company folio
            frm.add_custom_button(__('Record Transaction'), function () {
                make_company_debit_entry(frm);
            }, 'Actions');
        }

        // Button: Create Invoice
        if (frm.doc.status !== 'Provisional') {
            frm.add_custom_button(__('Create Invoice'), function () {
                frappe.confirm(
                    'Create Sales Invoice for all unbilled items?',
                    function () {
                        frm.call({
                            method: 'hospitality_core.hospitality_core.api.invoicing.create_invoice_from_folio',
                            args: {
                                folio_name: frm.doc.name
                            },
                            freeze: true,
                            callback: function (r) {
                                if (!r.exc && r.message) {
                                    frappe.msgprint('Invoice Created: ' + r.message);
                                    frappe.set_route('Form', 'Sales Invoice', r.message);
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, 'Actions');
        }

        // Button: Move Transactions (Move Bill)
        let can_manage_folio = frappe.user_roles.includes('Frontdesk Supervisor') ||
            frappe.session.user === 'Administrator';

        if (frm.doc.status === 'Open' && can_manage_folio) {
            frm.add_custom_button(__('Move Transactions'), function () {
                move_transactions_dialog(frm);
            }, 'Actions');
        }

        // Button: Void Transaction
        if (frm.doc.status === 'Open' && can_manage_folio) {
            frm.add_custom_button(__('Void Transaction'), function () {
                void_transaction_dialog(frm);
            }, 'Actions');
        }

        // Highlight Balance
        if (frm.doc.outstanding_balance > 0.01) {
            frm.set_df_property('outstanding_balance', 'hidden', 0);
            frm.set_df_property('excess_payment', 'hidden', 1);
            frm.set_df_property('outstanding_balance', 'read_only', 1);
            $(frm.fields_dict['outstanding_balance'].wrapper).find('input').css('color', 'red').css('font-weight', 'bold');
        } else if (frm.doc.outstanding_balance < -0.01) {
            frm.set_df_property('outstanding_balance', 'hidden', 1);
            frm.set_df_property('excess_payment', 'hidden', 0);
            $(frm.fields_dict['excess_payment'].wrapper).find('input').css('color', 'green').css('font-weight', 'bold');
        } else {
            frm.set_df_property('outstanding_balance', 'hidden', 0);
            frm.set_df_property('excess_payment', 'hidden', 1);
        }

        // Highlight voided rows in the transactions grid
        highlight_voided_rows(frm);
    }
});

function highlight_voided_rows(frm) {
    // Wait a tick for the grid to render before applying styles
    setTimeout(() => {
        const grid = frm.fields_dict['transactions'] && frm.fields_dict['transactions'].grid;
        if (!grid) return;

        frm.doc.transactions.forEach((row, idx) => {
            const $row = grid.grid_rows[idx] && $(grid.grid_rows[idx].wrapper);
            if (!$row) return;

            if (row.is_void) {
                $row.css({
                    'background-color': '#fff3f3',
                    'text-decoration': 'line-through',
                    'color': '#999',
                    'opacity': '0.7'
                });
                // Add a "VOID" badge if not already present
                if (!$row.find('.void-badge').length) {
                    $row.find('.data-row').prepend(
                        '<span class="void-badge" style="background:#dc3545;color:#fff;font-size:10px;padding:1px 5px;border-radius:3px;margin-right:5px;text-decoration:none;font-weight:bold;vertical-align:middle;">VOID</span>'
                    );
                }
            } else {
                $row.css({ 'background-color': '', 'text-decoration': '', 'color': '', 'opacity': '' });
            }
        });
    }, 100);
}

frappe.ui.form.on('Folio Transaction', {
    item: function (frm, cdt, cdn) {
        // Automatically fetch price when Item is selected
        var row = locals[cdt][cdn];
        if (row.item) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Item Price",
                    filters: { item_code: row.item, price_list: "Standard Selling" }, // Adjust Price List as needed
                    fieldname: "price_list_rate"
                },
                callback: function (r) {
                    let rate = 0;
                    if (r.message && r.message.price_list_rate) {
                        rate = r.message.price_list_rate;
                    } else {
                        // Fallback: Get Standard Rate from Item
                        frappe.db.get_value("Item", row.item, "standard_rate", (val) => {
                            if (val && val.standard_rate) {
                                frappe.model.set_value(cdt, cdn, "amount", val.standard_rate * row.qty);
                            }
                        });
                        return;
                    }
                    frappe.model.set_value(cdt, cdn, "amount", rate * row.qty);
                }
            });

            // Default Description
            frappe.db.get_value("Item", row.item, "item_name", (r) => {
                if (r && r.item_name) frappe.model.set_value(cdt, cdn, "description", r.item_name);
            });
        }
    },

    qty: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        // Recalculate amount if rate known, or simple logic
        // This is a basic implementation. Ideally store rate separately.
    }
});

function move_transactions_dialog(frm) {
    // Filter valid transactions (not void, not invoiced)
    let valid_txns = frm.doc.transactions.filter(t => !t.is_void && !t.is_invoiced).map(t => {
        return { label: `${t.posting_date}: ${t.description} (${t.amount})`, value: t.name }
    });

    if (valid_txns.length === 0) {
        frappe.msgprint("No movable transactions found.");
        return;
    }

    var d = new frappe.ui.Dialog({
        title: 'Move Transactions to Another Folio',
        fields: [
            {
                label: 'Select Transactions',
                fieldname: 'transactions',
                fieldtype: 'MultiSelect', // Or Table MultiSelect depending on version
                options: valid_txns,
                reqd: 1,
                description: 'Ctrl+Click to select multiple'
            },
            {
                label: 'Target Folio',
                fieldname: 'target_folio',
                fieldtype: 'Link',
                options: 'Guest Folio',
                get_query: function () {
                    return {
                        filters: {
                            'status': 'Open',
                            'name': ['!=', frm.doc.name]
                        }
                    };
                },
                reqd: 1
            }
        ],
        primary_action_label: 'Move',
        primary_action: function (values) {
            // MultiSelect returns array of values or comma separated string
            let txn_list = values.transactions;
            if (typeof txn_list === 'string') {
                txn_list = txn_list.split(',').map(s => s.trim());
            }

            frappe.call({
                method: 'hospitality_core.hospitality_core.api.folio.move_transactions',
                args: {
                    transaction_names: txn_list,
                    target_folio: values.target_folio
                },
                freeze: true,
                callback: function (r) {
                    if (!r.exc) {
                        frappe.msgprint(__("Transactions moved successfully"));
                        d.hide();
                        frm.reload_doc();
                    }
                }
            });
        }
    });
    d.show();
}

function void_transaction_dialog(frm) {
    // Include regular transactions (not invoiced), POS Invoice transactions, and Payment Entry transactions
    let valid_txns = frm.doc.transactions.filter(t => {
        if (t.is_void) return false;
        // Always allow voiding POS Invoice and Payment Entry postings even if is_invoiced=1
        if (t.reference_doctype === 'POS Invoice') return true;
        if (t.reference_doctype === 'Payment Entry') return true;
        // Exclude already-invoiced (sales invoice) regular transactions
        if (t.is_invoiced) return false;
        return true;
    });

    if (valid_txns.length === 0) {
        frappe.msgprint("No voidable transactions found.");
        return;
    }

    // Build a label -> name map. Frappe's Select field always returns the
    // selected string, so we need to reverse-look up the row name from it.
    let label_to_name = {};
    let option_labels = valid_txns.map(t => {
        let type_tag = '';
        if (t.reference_doctype === 'POS Invoice') type_tag = ' [POS]';
        else if (t.reference_doctype === 'Payment Entry') type_tag = ' [Payment]';
        let label = `${t.posting_date} - ${t.description} (${t.amount})${type_tag}`;
        label_to_name[label] = t.name;
        return label;
    });

    var d = new frappe.ui.Dialog({
        title: 'Void Transaction',
        fields: [
            {
                label: 'Select Transaction',
                fieldname: 'transaction',
                fieldtype: 'Select',
                options: option_labels,
                reqd: 1
            },
            {
                label: 'Reason Code',
                fieldname: 'reason',
                fieldtype: 'Link',
                options: 'Allowance Reason Code',
                reqd: 1
            }
        ],
        primary_action_label: 'Void',
        primary_action: function (values) {
            // Resolve the actual Folio Transaction name from the displayed label
            let txn_name = label_to_name[values.transaction];
            if (!txn_name) {
                frappe.msgprint(__("Could not identify selected transaction. Please try again."));
                return;
            }

            frappe.call({
                method: 'hospitality_core.hospitality_core.api.financial_control.void_transaction',
                args: {
                    folio_transaction_name: txn_name,
                    reason_code: values.reason
                },
                freeze: true,
                callback: function (r) {
                    if (!r.exc) {
                        d.hide();
                        frm.reload_doc();
                    }
                }
            });
        }
    });
    d.show();
}

function make_payment_entry(frm) {
    // Build simple dialog: Amount, Mode of Payment (Reception only), Hotel Reception
    var d = new frappe.ui.Dialog({
        title: __('Record Payment'),
        fields: [
            {
                label: __('Guest'),
                fieldname: 'guest_display',
                fieldtype: 'Data',
                read_only: 1,
                default: frm.doc.guest || ''
            },
            {
                label: __('Room'),
                fieldname: 'room_display',
                fieldtype: 'Data',
                read_only: 1,
                default: frm.doc.room || ''
            },
            {
                label: __('Outstanding Balance'),
                fieldname: 'balance_display',
                fieldtype: 'Currency',
                read_only: 1,
                default: frm.doc.outstanding_balance || 0
            },
            { fieldtype: 'Section Break' },
            {
                label: __('Amount'),
                fieldname: 'amount',
                fieldtype: 'Currency',
                reqd: 1,
                default: frm.doc.outstanding_balance > 0 ? frm.doc.outstanding_balance : 0,
                description: __('Enter amount being received')
            },
            {
                label: __('Mode of Payment'),
                fieldname: 'mode_of_payment',
                fieldtype: 'Link',
                options: 'Mode of Payment',
                reqd: 1,
                get_query: function () {
                    return {
                        filters: [['Mode of Payment', 'name', 'like', '%Reception%']]
                    };
                },
                description: __('Only reception-linked payment modes shown')
            },
            {
                label: __('Hotel Reception'),
                fieldname: 'hotel_reception',
                fieldtype: 'Link',
                options: 'Hotel Reception',
                reqd: 1,
                description: __('Select the receiving reception')
            }
        ],
        primary_action_label: __('Submit Payment'),
        primary_action: function (values) {
            d.hide();
            frappe.dom.freeze(__('Processing payment...'));

            frappe.call({
                method: 'hospitality_core.hospitality_core.api.payment_bridge.create_folio_payment',
                args: {
                    folio_name:       frm.doc.name,
                    amount:           values.amount,
                    mode_of_payment:  values.mode_of_payment,
                    hotel_reception:  values.hotel_reception
                },
                callback: function (r) {
                    frappe.dom.unfreeze();
                    if (!r.exc && r.message) {
                        frappe.show_alert({
                            message: __('Payment {0} recorded successfully', [r.message]),
                            indicator: 'green'
                        }, 6);
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

function issue_refund_dialog(frm) {
    let excess_balance = Math.abs(frm.doc.outstanding_balance);
    
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
                default: excess_balance
            },
            { fieldtype: 'Section Break' },
            {
                label: __('Refund Amount'),
                fieldname: 'amount',
                fieldtype: 'Currency',
                reqd: 1,
                default: excess_balance,
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
            if (values.amount > excess_balance + 0.01) {
                frappe.msgprint(__('Refund amount cannot exceed available credit.'));
                return;
            }
            d.hide();
            frappe.dom.freeze(__('Processing refund...'));

            frappe.call({
                method: 'hospitality_core.hospitality_core.api.payment_bridge.issue_folio_refund',
                args: {
                    folio_name:       frm.doc.name,
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

// ─── Company Folio: Record Payment to Company (offsets city ledger balance) ───
function make_company_payment_entry(frm) {
    var d = new frappe.ui.Dialog({
        title: __('Record Payment to Company'),
        fields: [
            {
                label: __('Company'),
                fieldname: 'company_display',
                fieldtype: 'Data',
                read_only: 1,
                default: frm.doc.company || ''
            },
            {
                label: __('Outstanding Balance (City Ledger)'),
                fieldname: 'balance_display',
                fieldtype: 'Currency',
                read_only: 1,
                default: frm.doc.outstanding_balance || 0
            },
            { fieldtype: 'Section Break' },
            {
                label: __('Amount'),
                fieldname: 'amount',
                fieldtype: 'Currency',
                reqd: 1,
                default: frm.doc.outstanding_balance > 0 ? frm.doc.outstanding_balance : 0,
                description: __('Amount received from the company to offset city ledger')
            },
            {
                label: __('Mode of Payment'),
                fieldname: 'mode_of_payment',
                fieldtype: 'Link',
                options: 'Mode of Payment',
                reqd: 1,
                get_query: function () {
                    return {
                        filters: [['Mode of Payment', 'name', 'like', '%Reception%']]
                    };
                },
                description: __('Only reception-linked payment modes shown')
            },
            {
                label: __('Hotel Reception'),
                fieldname: 'hotel_reception',
                fieldtype: 'Link',
                options: 'Hotel Reception',
                reqd: 1,
                description: __('Select the receiving reception')
            },
            {
                label: __('Reference / Cheque No'),
                fieldname: 'reference_no',
                fieldtype: 'Data',
                description: __('Optional: Bank reference, cheque number, etc.')
            },
            {
                label: __('Narration / Remarks'),
                fieldname: 'remarks',
                fieldtype: 'Small Text'
            }
        ],
        primary_action_label: __('Record Payment'),
        primary_action: function (values) {
            if (!values.amount || values.amount <= 0) {
                frappe.msgprint(__('Please enter a valid amount.'));
                return;
            }
            d.hide();
            frappe.dom.freeze(__('Recording company payment...'));

            frappe.call({
                method: 'hospitality_core.hospitality_core.api.payment_bridge.create_company_folio_payment',
                args: {
                    folio_name: frm.doc.name,
                    amount: values.amount,
                    mode_of_payment: values.mode_of_payment,
                    hotel_reception: values.hotel_reception,
                    reference_no: values.reference_no || '',
                    remarks: values.remarks || ''
                },
                callback: function (r) {
                    frappe.dom.unfreeze();
                    if (!r.exc && r.message) {
                        frappe.show_alert({
                            message: __('Payment {0} recorded successfully', [r.message]),
                            indicator: 'green'
                        }, 6);
                        // Open the Payment Entry so the user can print the receipt
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

// ─── Company Folio: Record Transaction (manual debit to city ledger) ─────────
function make_company_debit_entry(frm) {
    var d = new frappe.ui.Dialog({
        title: __('Record Transaction (Debit)'),
        fields: [
            {
                label: __('Company'),
                fieldname: 'company_display',
                fieldtype: 'Data',
                read_only: 1,
                default: frm.doc.company || ''
            },
            { fieldtype: 'Section Break' },
            {
                label: __('Item / Charge Code'),
                fieldname: 'item',
                fieldtype: 'Link',
                options: 'Item',
                reqd: 1,
                description: __('Select the item or service being charged')
            },
            {
                label: __('Description'),
                fieldname: 'description',
                fieldtype: 'Data',
                reqd: 1
            },
            {
                label: __('Quantity'),
                fieldname: 'qty',
                fieldtype: 'Float',
                default: 1,
                reqd: 1
            },
            {
                label: __('Amount'),
                fieldname: 'amount',
                fieldtype: 'Currency',
                reqd: 1,
                description: __('Positive debit amount to be posted to the city ledger')
            },
            {
                label: __('Posting Date'),
                fieldname: 'posting_date',
                fieldtype: 'Date',
                default: frappe.datetime.get_today(),
                reqd: 1
            },
            {
                label: __('Remarks'),
                fieldname: 'remarks',
                fieldtype: 'Small Text'
            }
        ],
        primary_action_label: __('Post Transaction'),
        primary_action: function (values) {
            if (!values.amount || values.amount <= 0) {
                frappe.msgprint(__('Amount must be a positive value for a debit entry.'));
                return;
            }
            d.hide();
            frappe.dom.freeze(__('Posting transaction...'));

            frappe.call({
                method: 'hospitality_core.hospitality_core.api.payment_bridge.create_company_folio_transaction',
                args: {
                    folio_name: frm.doc.name,
                    item: values.item,
                    description: values.description,
                    qty: values.qty,
                    amount: values.amount,
                    posting_date: values.posting_date,
                    remarks: values.remarks || ''
                },
                callback: function (r) {
                    frappe.dom.unfreeze();
                    if (!r.exc && r.message) {
                        frappe.show_alert({
                            message: __('Transaction {0} posted successfully', [r.message]),
                            indicator: 'blue'
                        }, 6);
                        frm.reload_doc();
                    }
                },
                error: function () {
                    frappe.dom.unfreeze();
                }
            });
        }
    });

    // Auto-fill description when item is selected
    d.fields_dict['item'].df.onchange = function () {
        let item = d.get_value('item');
        if (item) {
            frappe.db.get_value('Item', item, 'item_name', function (r) {
                if (r && r.item_name) {
                    d.set_value('description', r.item_name);
                }
            });
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Item Price',
                    filters: { item_code: item, price_list: 'Standard Selling' },
                    fieldname: 'price_list_rate'
                },
                callback: function (r) {
                    if (r.message && r.message.price_list_rate) {
                        let qty = d.get_value('qty') || 1;
                        d.set_value('amount', r.message.price_list_rate * qty);
                    }
                }
            });
        }
    };

    d.show();
}