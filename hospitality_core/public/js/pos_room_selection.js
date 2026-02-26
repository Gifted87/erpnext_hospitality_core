
frappe.provide('hospitality.pos');

hospitality.pos.RoomSelector = class {
    constructor() {
        this.current_room = null;
        this.has_hooked_pos = false;
        this.init();
    }

    init() {
        // Robust polling mechanism to wait for PointOfSale components
        console.log("Initializing Hospitality Room Selector...");
        const interval = setInterval(() => {
            if (window.erpnext && erpnext.PointOfSale && erpnext.PointOfSale.ItemCart) {
                clearInterval(interval);
                this.hook_pos_components();
            }
        }, 500);

        // Safety timeout - stop polling after 30 seconds
        setTimeout(() => clearInterval(interval), 30000);
    }

    bind_events() {
        // Defensive addition to prevent "bind_events is not a function" 
        // or errors if legacy code calls this explicitly.
        console.log("RoomSelector.bind_events called (defensive)");
    }

    hook_pos_components() {
        if (this.has_hooked_pos) return;
        this.has_hooked_pos = true;

        console.log("Hooking into erpnext.PointOfSale.ItemCart");

        const me = this;

        // 1. Monkey-patch update_customer_section to re-inject our field
        const original_update = erpnext.PointOfSale.ItemCart.prototype.update_customer_section;
        erpnext.PointOfSale.ItemCart.prototype.update_customer_section = function () {
            original_update.apply(this, arguments);
            me.render_room_input(this.$customer_section);
        };

        // 2. Monkey-patch make_customer_selector for the initial/reset state
        const original_make = erpnext.PointOfSale.ItemCart.prototype.make_customer_selector;
        erpnext.PointOfSale.ItemCart.prototype.make_customer_selector = function () {
            original_make.apply(this, arguments);
            me.render_room_input(this.$customer_section);
        };

        // 3. Hook into Customer change to auto-fill room if possible
        frappe.ui.form.on('POS Invoice', {
            customer: function (frm) {
                if (frm.doc.customer && !frm.doc.hotel_room) {
                    me.lookup_room_by_customer(frm.doc.customer);
                }
            },
            validate: function (frm) {
                me.sync_to_model(frm);
            },
            before_save: function (frm) {
                me.sync_to_model(frm);
            }
        });

        // Initial render if already loaded
        if (window.cur_pos && window.cur_pos.cart) {
            this.render_room_input(window.cur_pos.cart.$customer_section);
        }
    }

    render_room_input($container) {
        if (!$container || $container.find('#pos-room-number').length > 0) return;

        console.log("Rendering Room Number input into POS UI");

        const room_input_html = `
            <div class="pos-room-selector" style="margin: 10px 0; padding: 8px; background: #f0f4f7; border-radius: 8px; border: 1px solid #d1d8dd;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                    <label style="font-size: 11px; font-weight: bold; color: #444; margin: 0;">Room Number</label>
                    <div id="room-lookup-status" style="font-size: 10px; font-weight: 500;"></div>
                </div>
                <div class="control-input-wrapper">
                    <input type="text" id="pos-room-number" class="form-control" placeholder="Type Room No..." 
                           style="background-color: white; height: 32px; font-size: 13px; border-radius: 4px;">
                </div>
            </div>
        `;

        // Prepend to the container (usually .customer-section)
        $container.prepend(room_input_html);

        const $input = $('#pos-room-number');
        if (this.current_room) $input.val(this.current_room);

        $input.on('change', (e) => {
            this.handle_manual_room_input(e.target.value);
        });
    }

    handle_manual_room_input(room_no) {
        this.current_room = room_no;
        const $status = $('#room-lookup-status');

        if (!room_no) {
            $status.html('');
            this.sync_to_model();
            return;
        }

        $status.html('<span style="color: #666;">Searching...</span>');

        frappe.call({
            method: 'hospitality_core.hospitality_core.api.pos_bridge.get_guest_details_from_room',
            args: { room_number: room_no },
            callback: (r) => {
                if (r.message && !r.message.error) {
                    const guest = r.message;
                    $status.html(`<span style="color: #28a745;">✔ ${guest.customer_name}</span>`);
                    this.set_pos_customer(guest.customer);
                    this.sync_to_model(null, room_no);
                } else {
                    const error = r.message ? r.message.error : 'Not found';
                    $status.html(`<span style="color: #dc3545;">✘ ${error}</span>`);
                }
            }
        });
    }

    lookup_room_by_customer(customer) {
        // Auto-lookup room if customer is selected manually
        const $status = $('#room-lookup-status');
        $status.html('<span style="color: #666;">Folio?...</span>');

        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'Guest Folio',
                filters: { customer: customer, status: 'Open' },
                fieldname: 'room'
            },
            callback: (r) => {
                if (r.message && r.message.room) {
                    const room = r.message.room;
                    this.current_room = room;
                    $('#pos-room-number').val(room);
                    $status.html(`<span style="color: #28a745;">✔ Folio Room: ${room}</span>`);
                    this.sync_to_model(null, room);
                } else {
                    $status.html('');
                }
            }
        });
    }

    sync_to_model(frm, room_no) {
        const val = room_no || this.current_room;
        if (!val) return;

        const target_frm = frm || (window.cur_pos ? window.cur_pos.frm : null);
        if (target_frm && target_frm.doc.doctype === 'POS Invoice') {
            console.log("Syncing room to model:", val);
            frappe.model.set_value(target_frm.doc.doctype, target_frm.doc.name, 'hotel_room', val);
        }
    }

    set_pos_customer(customer_id) {
        if (!customer_id) return;

        const frm = (window.cur_pos ? window.cur_pos.frm : null);
        if (frm) {
            frappe.model.set_value(frm.doc.doctype, frm.doc.name, 'customer', customer_id);
            // Trigger UI update in POS cart if possible
            if (window.cur_pos.cart) {
                window.cur_pos.cart.fetch_customer_details(customer_id).then(() => {
                    window.cur_pos.cart.update_customer_section();
                });
            }
        }
    }
};

// Initialize
$(document).ready(() => {
    hospitality.pos.room_selector = new hospitality.pos.RoomSelector();
});
