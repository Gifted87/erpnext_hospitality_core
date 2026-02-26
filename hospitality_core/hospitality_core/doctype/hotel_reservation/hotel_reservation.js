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
                        `Are you sure you want to Check Out <b>${frm.doc.guest}</b> from Room <b>${frm.doc.room}</b>?<br><br>This will close the folio and mark the room as Dirty.`,
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

            // Read-Only Logic for Checked In, Checked Out, and Cancelled
            if (['Checked In', 'Checked Out', 'Cancelled'].includes(frm.doc.status)) {
                let exceptions = [];
                if (frm.doc.status === 'Checked In') {
                    exceptions = ['departure_date', 'discount_value'];
                }

                // Selectively lock fields WITHOUT calling frm.set_read_only()
                // which would hide the save button and cause issues
                if (frm.fields_dict) {
                    Object.keys(frm.fields_dict).forEach(fieldname => {
                        let field = frm.fields_dict[fieldname];
                        // Skip non-data fields
                        if (!field || !field.df) return;

                        let is_readonly = !exceptions.includes(fieldname);
                        frm.set_df_property(fieldname, 'read_only', is_readonly ? 1 : 0);
                    });
                }
            } else {
                // Ensure all fields are editable when status is not in restricted states
                if (frm.fields_dict) {
                    Object.keys(frm.fields_dict).forEach(fieldname => {
                        let field = frm.fields_dict[fieldname];
                        if (!field || !field.df) return;
                        frm.set_df_property(fieldname, 'read_only', 0);
                    });
                }
            }
        }
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
                                        'status': 'Available',
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
        // Clear room if type changes
        frm.set_value('room', '');
    },

    arrival_date: function (frm) {
        calculate_nights(frm);
        validate_room_availability(frm);
    },

    departure_date: function (frm) {
        calculate_nights(frm);
        validate_room_availability(frm);
    }
});

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