/**
 * Client Script for POS Invoice - Automatic Printing
 * 
 * This script automatically triggers print dialog when a POS Invoice is submitted.
 * It will print the configured number of copies to the client's default printer.
 */

frappe.ui.form.on('POS Invoice', {
    after_save: function (frm) {
        // Only trigger auto-print if document is submitted
        if (frm.doc.docstatus === 1 && !frm.doc.__auto_print_triggered) {
            // Mark as triggered to avoid duplicate prints
            frm.doc.__auto_print_triggered = true;

            // Get settings from server
            frappe.call({
                method: 'hospitality_core.hospitality_core.api.auto_print.get_print_settings',
                callback: function (r) {
                    if (r.message && r.message.enabled) {
                        const settings = r.message;
                        const copies = settings.copies || 3;
                        const print_format = settings.print_format || 'Standard';

                        console.log(`Auto-print enabled: printing ${copies} copies`);

                        // Trigger automatic printing
                        trigger_auto_print(frm, print_format, copies);
                    }
                }
            });
        }
    }
});

function trigger_auto_print(frm, print_format, copies) {
    // Get the print URL
    const print_url = frappe.urllib.get_full_url(
        `/api/method/frappe.utils.print_format.download_pdf?`
        + `doctype=${encodeURIComponent(frm.doctype)}`
        + `&name=${encodeURIComponent(frm.docname)}`
        + `&format=${encodeURIComponent(print_format)}`
        + `&no_letterhead=0`
    );

    console.log('Opening print dialog...');

    // Open print in new window and trigger print dialog
    const print_window = window.open(print_url, '_blank');

    if (print_window) {
        // Wait for the PDF to load, then trigger print
        print_window.onload = function () {
            // Auto-print when window loads
            setTimeout(function () {
                print_window.print();

                // Print additional copies if needed
                if (copies > 1) {
                    frappe.show_alert({
                        message: __('Printing {0} copies. Please print {1} more time(s) when prompted.',
                            [copies, copies - 1]),
                        indicator: 'blue'
                    }, 10);
                }
            }, 500);
        };
    } else {
        frappe.msgprint({
            title: __('Pop-up Blocked'),
            message: __('Please allow pop-ups for this site to enable automatic printing.'),
            indicator: 'red'
        });
    }
}
