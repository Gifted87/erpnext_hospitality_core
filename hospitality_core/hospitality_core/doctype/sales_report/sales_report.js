// Copyright (c) 2026, Gift Braimah and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Report", {
	refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button("Generate Report", () => {
                frappe.call({
                    doc: frm.doc,
                    method: "generate_report",
                    freeze: true,
                    freeze_message: "Generating End of Day Sales Report...",
                    callback: function(r) {
                        if (!r.exc) {
                            frm.reload_doc();
                        }
                    }
                });
            }).addClass("btn-primary");

            frm.add_custom_button("Print Report", () => {
                frm.print_doc();
            });
        }
	},
    company(frm) {
        // Just to set default name based on company if needed
    }
});
