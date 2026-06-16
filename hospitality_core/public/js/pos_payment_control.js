/**
 * Hospitality POS Payment Control
 *
 * Rules enforced on the POS PAYMENT screen:
 *
 * 1. Room is entered -> ONLY "Guest Account" is selectable.
 *    Full amount is forced to Guest Account. Others are 0.
 *
 * 2. Non-Walk-In customer + NO room -> ONLY "Complimentary" is selectable.
 *    Full amount is forced to Complimentary. Others are 0.
 *
 * 3. Walk-In Customer + NO room -> Guest Account & Complimentary are blocked.
 *    All others are selectable.
 *
 * 4. Any other case -> No restrictions.
 */

frappe.provide('hospitality.pos.payment_control');

(function () {

    const GUEST_ACCOUNT_MODE  = 'Guest Account';
    const COMPLIMENTARY_MODE  = 'Complimentary';
    const WALKIN_CUSTOMER     = 'Walk in Customer';

    /* ── Helpers ─────────────────────────────────────────────────────────── */

    function get_room() {
        const v = ($('#pos-room-number').val() || '').trim();
        if (v) return v;
        if (window.cur_pos && cur_pos.frm) return cur_pos.frm.doc.hotel_room || '';
        return '';
    }

    function get_customer() {
        if (window.cur_pos && cur_pos.frm) return cur_pos.frm.doc.customer || '';
        return '';
    }

    /**
     * Determines the current restriction state.
     * Returns an object: { force_mode: "mode" | null, blocked_modes: ["mode"] }
     */
    function get_restriction_state() {
        const room = get_room();
        const customer = get_customer();

        if (room) {
            return { force_mode: GUEST_ACCOUNT_MODE, blocked_modes: [] }; // Everything but force_mode will be blocked
        } else if (customer && customer !== WALKIN_CUSTOMER) {
            return { force_mode: COMPLIMENTARY_MODE, blocked_modes: [] };
        } else if (customer === WALKIN_CUSTOMER && !room) {
            return { force_mode: null, blocked_modes: [GUEST_ACCOUNT_MODE, COMPLIMENTARY_MODE] };
        } else {
            return { force_mode: null, blocked_modes: [] };
        }
    }

    /* ── Amount Enforcer ─────────────────────────────────────────────────── */

    function enforce_amounts() {
        if (!window.cur_pos || !cur_pos.payment || !cur_pos.frm || !cur_pos.frm.doc) return false;
        
        const state = get_restriction_state();
        if (!state.force_mode) return false;

        const doc = cur_pos.frm.doc;
        const grand_total = doc.grand_total || 0;
        let amounts_changed = false;

        // Make sure the target mode exists in doc.payments
        let found_target = doc.payments.find(r => r.mode_of_payment === state.force_mode);
        if (!found_target) {
            const new_row = frappe.model.add_child(doc, 'Sales Invoice Payment', 'payments');
            new_row.mode_of_payment = state.force_mode;
            new_row.amount = 0;
            // Force re-render of DOM so the control is created
            if (cur_pos.payment.render_payment_mode_dom) {
                cur_pos.payment.render_payment_mode_dom();
            }
        }

        // Use ERPNext's UI controls to safely update the values without triggering infinite loops
        doc.payments.forEach(p => {
            let mode_class = p.mode_of_payment;
            if (cur_pos.payment.sanitize_mode_of_payment) {
                mode_class = cur_pos.payment.sanitize_mode_of_payment(p.mode_of_payment);
            } else {
                mode_class = mode_class.toLowerCase().replace(/[^a-zA-Z0-9]/g, '-');
            }
            
            const ctrl = cur_pos.payment[`${mode_class}_control`];
            if (ctrl) {
                if (p.mode_of_payment === state.force_mode) {
                    if (ctrl.get_value() !== grand_total) {
                        ctrl.set_value(grand_total);
                        amounts_changed = true;
                    }
                } else {
                    if (ctrl.get_value() !== 0) {
                        ctrl.set_value(0);
                        amounts_changed = true;
                    }
                }
            }
        });

        return amounts_changed;
    }

    /* ── Visual restriction ───────────────────────────────────────────────── */

    function apply_visual_restrictions() {
        const state = get_restriction_state();

        const wrappers = document.querySelectorAll(
            '.payment-modes .mode-of-payment-wrapper, ' +
            '.payment-mode-wrapper, ' +
            '[data-payment-mode]'
        );

        if (!wrappers.length) return;

        wrappers.forEach(function (el) {
            const name_el = el.querySelector('.mode-of-payment') ||
                            el.querySelector('.payment-mode-name') ||
                            el;
            const mode_name = (name_el.textContent || '').trim() ||
                              el.dataset.paymentMode || '';

            if (!mode_name) return;

            let is_blocked = false;
            
            if (state.force_mode) {
                is_blocked = (mode_name !== state.force_mode);
            } else {
                is_blocked = state.blocked_modes.includes(mode_name);
            }

            if (is_blocked) {
                el.style.opacity       = '0.30';
                el.style.filter        = 'grayscale(60%)';
                el.style.pointerEvents = 'none';
                el.style.cursor        = 'not-allowed';
                el.classList.add('hcore-payment-blocked');
            } else {
                el.style.opacity       = '';
                el.style.filter        = '';
                el.style.pointerEvents = '';
                el.style.cursor        = '';
                el.classList.remove('hcore-payment-blocked');
            }
        });

        // Disable the amount inputs of blocked modes
        document.querySelectorAll('.hcore-payment-blocked input').forEach(function (inp) {
            inp.setAttribute('disabled', 'disabled');
            inp.style.background = '#f5f5f5';
        });
        document.querySelectorAll(
            '.payment-modes .mode-of-payment-wrapper:not(.hcore-payment-blocked) input'
        ).forEach(function (inp) {
            inp.removeAttribute('disabled');
            inp.style.background = '';
        });
    }

    /* ── Native capture-phase click blocker ──────────────────────────────── */

    function on_payment_mode_click(e) {
        const state = get_restriction_state();
        
        let el = e.target;
        while (el && el !== document.body) {
            if (
                el.classList.contains('mode-of-payment-wrapper') ||
                el.classList.contains('payment-mode-wrapper') ||
                el.dataset.paymentMode
            ) {
                const name_el = el.querySelector('.mode-of-payment') ||
                                el.querySelector('.payment-mode-name') ||
                                el;
                const mode_name = (name_el.textContent || '').trim() ||
                                  el.dataset.paymentMode || '';

                if (!mode_name) return;

                let is_blocked = false;
                if (state.force_mode) {
                    is_blocked = (mode_name !== state.force_mode);
                } else {
                    is_blocked = state.blocked_modes.includes(mode_name);
                }

                if (is_blocked) {
                    e.stopImmediatePropagation();
                    e.preventDefault();
                    frappe.show_alert({
                        message: __('Payment mode "{0}" is not allowed for this customer/room combination.', [mode_name]),
                        indicator: 'orange'
                    }, 3);
                }
                return;
            }
            el = el.parentElement;
        }
    }

    document.addEventListener('click', on_payment_mode_click, true);

    /* ── MutationObserver — re-apply when payment DOM changes ────────────── */

    const observer = new MutationObserver(function (mutations) {
        let needs_update = false;
        for (const m of mutations) {
            for (const node of m.addedNodes) {
                if (node.nodeType === 1) {
                    const el = /** @type {Element} */ (node);
                    if (
                        el.classList.contains('payment-modes') ||
                        el.classList.contains('mode-of-payment-wrapper') ||
                        el.querySelector && (
                            el.querySelector('.payment-modes') ||
                            el.querySelector('.mode-of-payment-wrapper')
                        )
                    ) {
                        needs_update = true;
                        break;
                    }
                }
            }
            if (needs_update) break;
        }
        if (needs_update) {
            setTimeout(apply_visual_restrictions, 50);
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });

    /* ── Monkey-patch ERPNext Payment component ─── */

    function try_patch_payment_component() {
        if (window.erpnext && erpnext.PointOfSale && erpnext.PointOfSale.Payment) {
            const proto = erpnext.PointOfSale.Payment.prototype;

            if (proto.render_payment_section && !proto._hcore_patched_render) {
                const orig = proto.render_payment_section;
                proto.render_payment_section = function () {
                    orig.apply(this, arguments);
                    // Run enforcement AFTER ERPNext finishes setting defaults
                    setTimeout(() => {
                        enforce_amounts();
                        apply_visual_restrictions();
                        // Force a click on the valid mode so it becomes visually active/focused
                        const state = get_restriction_state();
                        if (state.force_mode && this.sanitize_mode_of_payment) {
                            const mode_class = this.sanitize_mode_of_payment(state.force_mode);
                            const $mode_el = this.$payment_modes.find(`.${mode_class}.mode-of-payment-control`).parent();
                            if ($mode_el.length && !$mode_el.hasClass('border-primary')) {
                                $mode_el.click();
                            }
                        }
                    }, 50);
                };
                proto._hcore_patched_render = true;
            }

            if (proto.toggle_payment_section && !proto._hcore_patched_toggle) {
                const orig2 = proto.toggle_payment_section;
                proto.toggle_payment_section = function () {
                    orig2.apply(this, arguments);
                    setTimeout(() => {
                        enforce_amounts();
                        apply_visual_restrictions();
                    }, 50);
                };
                proto._hcore_patched_toggle = true;
            }

            return true;
        }
        return false;
    }

    // When the custom room input changes, refresh the payment screen if it's active
    $(document).on('change.hcore_pc input.hcore_pc', '#pos-room-number', function () {
        if (window.cur_pos && cur_pos.payment && cur_pos.payment.$payment_modes && cur_pos.payment.$payment_modes.is(':visible')) {
            enforce_amounts();
            setTimeout(apply_visual_restrictions, 50);
        }
    });

    // Poll until ERPNext POS is available
    const patch_interval = setInterval(function () {
        if (try_patch_payment_component()) clearInterval(patch_interval);
    }, 600);
    setTimeout(function () { clearInterval(patch_interval); }, 30000);

})();
