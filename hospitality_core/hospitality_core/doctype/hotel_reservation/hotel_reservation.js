frappe.ui.form.on('Hotel Reservation', {
    onload: function (frm) {
        if (frm.is_new()) {
            frm.set_value('status', 'Reserved');
            frm.set_value('is_company_guest', 0);
            frm.set_value('company', ''); // Ensure company is empty
        }
    },
    validate: function (frm) {
        if (!frm.doc.is_company_guest) {
            frm.set_value('company', null);
        }
    },
    is_company_guest: function (frm) {
        if (!frm.doc.is_company_guest) {
            frm.set_value('company', null);
        }
    },
    refresh: function (frm) {
        // Keep room type aligned with the selected room on load and refresh.
        sync_room_type_from_room(frm);

        // Filter Rooms based on Room Type AND Availability
        frm.set_query('room', function () {
            return {
                query: 'hospitality_core.hospitality_core.api.reservation.get_available_rooms_for_picker',
                filters: {
                    'arrival_date': frm.doc.arrival_date,
                    'departure_date': frm.doc.departure_date,
                    'room_type': frm.doc.room_type,
                    'ignore_reservation': frm.doc.name
                }
            };
        });

        // Add Workflow Buttons
        if (!frm.is_new()) {

            // CHECK IN BUTTON
            if (frm.doc.status === 'Reserved') {
                frm.add_custom_button(__('Check In'), function () {
                    frappe.confirm(
                        'Are you sure you want to Check In this guest?',
                        function () {
                            frm.call({
                                method: 'check_in_guest',
                                args: {
                                    name: frm.doc.name
                                },
                                freeze: true,
                                callback: function (r) {
                                    if (!r.exc) {
                                        frappe.msgprint('Guest Checked In Successfully');
                                        frm.reload_doc();
                                    }
                                }
                            });
                        }
                    );
                }).addClass("btn-primary");
            }

            // NEW CHECK OUT BUTTON (Primary Action)
            if (frm.doc.status === 'Checked In') {
                frm.page.set_primary_action(__('Check Out'), function () {
                    // Pre-check Departure Date
                    if (frm.doc.departure_date !== frappe.datetime.nowdate()) {
                        frappe.msgprint({
                            title: __('Early Departure?'),
                            message: __('Cannot Check Out. The Departure Date must be today. Please update the Departure Date/Shorten Stay first.'),
                            indicator: 'orange'
                        });
                        return;
                    }

                    // Nice Confirmation Dialog
                    frappe.warn(
                        'Confirm Checkout',
                        `Are you sure you want to Check Out <b>${frm.doc.guest}</b> from Room <b>${frm.doc.room}</b>?<br><br>This will close the folio and mark the room as Available.`,
                        function () {
                            frm.call({
                                method: 'check_out_guest',
                                args: {
                                    name: frm.doc.name
                                },
                                freeze: true,
                                freeze_message: __('Processing Checkout...'),
                                callback: function (r) {
                                    if (!r.exc) {
                                        frappe.show_alert({
                                            message: __('Guest Checked Out Successfully'),
                                            indicator: 'green'
                                        });
                                        frm.reload_doc();
                                    }
                                }
                            });
                        },
                        'Check Out'
                    );
                });
            }

            // CANCEL RESERVATION BUTTON
            // Visible for Reserved AND Checked In, Restricted to Supervisors
            let is_supervisor = frappe.user_roles.includes('Frontdesk Supervisor') ||
                frappe.user_roles.includes('System Manager') ||
                frappe.session.user === 'Administrator';

            if (['Reserved', 'Checked In'].includes(frm.doc.status) && is_supervisor) {
                frm.add_custom_button(__('Cancel Reservation'), function () {
                    frappe.confirm(
                        'Are you sure you want to Cancel this Reservation?',
                        function () {
                            frm.call({
                                method: 'cancel_reservation',
                                args: {
                                    name: frm.doc.name
                                },
                                freeze: true,
                                callback: function (r) {
                                    if (!r.exc) {
                                        frappe.msgprint('Reservation Cancelled.');
                                        frm.reload_doc();
                                    }
                                }
                            });
                        }
                    );
                }, null).addClass('btn-danger'); // Add class for styling if possible, or just standard custom button
            }

            // Quick Access to Folio
            if (frm.doc.folio) {
                frm.add_custom_button(__('Open Folio'), function () {
                    frappe.set_route('Form', 'Guest Folio', frm.doc.folio);
                }, 'View');
            }

        }

        set_reservation_read_only_state(frm);

        // ROOM MOVE BUTTON
        let can_move_room = frappe.user_roles.includes('Frontdesk Supervisor') ||
            frappe.session.user === 'Administrator';

        if (frm.doc.status === 'Checked In' && can_move_room) {
            frm.add_custom_button(__('Move Room'), function () {

                var d = new frappe.ui.Dialog({
                    title: 'Move Guest to New Room',
                    fields: [
                        {
                            label: 'New Room',
                            fieldname: 'new_room',
                            fieldtype: 'Link',
                            options: 'Hotel Room',
                            get_query: function () {
                                return {
                                    filters: {
                                        'is_enabled': 1,
                                        'name': ['!=', frm.doc.room]
                                    }
                                };
                            },
                            reqd: 1
                        }
                    ],
                    primary_action_label: 'Move',
                    primary_action: function (values) {
                        frm.call({
                            method: 'hospitality_core.hospitality_core.api.room_move.process_room_move',
                            args: {
                                reservation_name: frm.doc.name,
                                new_room: values.new_room
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

            }, __('Actions'));
        }
    },

    room_type: function (frm) {
        if (frm.__syncing_room_type) {
            return;
        }

        // Clear room if type changes
        frm.set_value('room', '');
    },

    arrival_date: function (frm) {
        calculate_nights(frm);
        validate_room_availability(frm);
        render_room_rate_preview(frm);
    },

    departure_date: function (frm) {
        calculate_nights(frm);
        validate_room_availability(frm);
    },
    
    room: function (frm) {
        sync_room_type_from_room(frm);
        render_room_rate_preview(frm);
    },
    
    rate_plan: function (frm) {
        render_room_rate_preview(frm);
    },
    
    discount_type: function (frm) {
        render_room_rate_preview(frm);
    },
    
    discount_value: function (frm) {
        render_room_rate_preview(frm);
    },
    
    is_complimentary: function (frm) {
        render_room_rate_preview(frm);
    }
});

function sync_room_type_from_room(frm) {
    if (!frm.doc.room) {
        return;
    }

    frappe.db.get_value('Hotel Room', frm.doc.room, 'room_type').then(r => {
        let room_type = r.message ? r.message.room_type : null;
        if (!room_type || frm.doc.room_type === room_type) {
            return;
        }

        frm.__syncing_room_type = true;
        return frm.set_value('room_type', room_type).then(() => {
            frm.__syncing_room_type = false;
            render_room_rate_preview(frm);
        });
    });
}

function set_reservation_read_only_state(frm) {
    if (!frm.fields_dict) return;

    let exceptions = [];
    if (frm.doc.status === 'Checked In') {
        exceptions = [
            'departure_date',
            'discount_value',
            'is_company_guest',
            'company',
            'allow_pos_posting'
        ];
    }

    let should_lock = ['Checked In', 'Checked Out', 'Cancelled'].includes(frm.doc.status);

    Object.keys(frm.fields_dict).forEach(fieldname => {
        let field = frm.fields_dict[fieldname];
        if (!field || !field.df) return;

        let is_readonly = fieldname === 'status' || (should_lock && !exceptions.includes(fieldname));
        frm.set_df_property(fieldname, 'read_only', is_readonly ? 1 : 0);
    });
}

function render_room_rate_preview(frm) {
    if (!frm.fields_dict.room_rate_preview) return;
    
    let wrapper = frm.fields_dict.room_rate_preview.$wrapper;
    
    if (!frm.doc.room) {
        wrapper.html("<div class='text-muted small'>Select a room to see rate.</div>");
        return;
    }
    
    // Show loading state
    wrapper.html("<div class='text-muted small'>Calculating rate...</div>");
    
    frappe.call({
        method: "hospitality_core.hospitality_core.api.reservation.get_room_rate",
        args: {
            room: frm.doc.room,
            rate_plan: frm.doc.rate_plan,
            room_type: frm.doc.room_type,
            arrival_date: frm.doc.arrival_date,
            discount_type: frm.doc.discount_type,
            discount_value: frm.doc.discount_value,
            is_complimentary: frm.doc.is_complimentary
        },
        callback: function(r) {
            if (r.message) {
                let d = r.message;
                let currency = frappe.boot.sysdefaults.currency;
                
                let html = `<div style="padding: 15px; border: 1px solid #d1d8dd; border-radius: 4px; background-color: #f7fafc;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span class="text-muted">Base Rate:</span>
                        <span style="font-weight: 500;">${format_currency(d.base_rate, currency)}</span>
                    </div>`;
                    
                if (d.discount_amount > 0) {
                    html += `<div style="display: flex; justify-content: space-between; margin-bottom: 5px; color: #e74c3c;">
                        <span>Discount:</span>
                        <span>- ${format_currency(d.discount_amount, currency)}</span>
                    </div>`;
                }
                
                html += `<div style="display: flex; justify-content: space-between; margin-top: 10px; padding-top: 10px; border-top: 1px solid #d1d8dd;">
                        <span style="font-weight: 600; font-size: 1.1em;">Final Rate / Night:</span>
                        <span style="font-weight: 700; font-size: 1.1em; color: #2ecc71;">${format_currency(d.final_rate, currency)}</span>
                    </div>
                </div>`;
                
                wrapper.html(html);
            }
        }
    });
}

function calculate_nights(frm) {
    if (frm.doc.arrival_date && frm.doc.departure_date) {
        var diff = frappe.datetime.get_diff(frm.doc.departure_date, frm.doc.arrival_date);
        if (diff < 1) {
            frappe.msgprint("Departure must be after Arrival");
        }
    }
}

function validate_room_availability(frm) {
    if (frm.doc.room && frm.doc.arrival_date && frm.doc.departure_date) {
        frappe.call({
            method: "hospitality_core.hospitality_core.api.reservation.check_availability",
            args: {
                room: frm.doc.room,
                arrival_date: frm.doc.arrival_date,
                departure_date: frm.doc.departure_date,
                ignore_reservation: frm.doc.name
            },
            callback: function (r) {
                if (r.exc) {
                    frm.set_value('room', '');
                }
            }
        });
    }
}