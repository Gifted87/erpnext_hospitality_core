// Copyright (c) 2026, Gift Braimah and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Recipe', {
    refresh: function (frm) {
        // Add custom buttons
        if (!frm.is_new()) {
            frm.add_custom_button(__('View BOM'), function () {
                if (frm.doc.bom) {
                    frappe.set_route('Form', 'BOM', frm.doc.bom);
                } else {
                    frappe.msgprint(__('BOM not yet created'));
                }
            });

            frm.add_custom_button(__('Calculate Cost'), function () {
                calculate_total_cost(frm);
            });
        }
    },

    item: function (frm) {
        if (frm.doc.item) {
            // Fetch item details
            frappe.db.get_value('Item', frm.doc.item, ['item_name', 'stock_uom', 'is_composite_item'])
                .then(r => {
                    if (r.message) {
                        frm.set_value('item_name', r.message.item_name);
                        frm.set_value('uom', r.message.stock_uom);

                        if (!r.message.is_composite_item) {
                            frappe.msgprint({
                                title: __('Warning'),
                                indicator: 'orange',
                                message: __('Item {0} is not marked as a Composite Item. Please enable it in the Item master.', [frm.doc.item])
                            });
                        }
                    }
                });
        }
    }
});

frappe.ui.form.on('Recipe Ingredient', {
    ingredient_item: function (frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.ingredient_item) {
            // Fetch stock UOM and set default UOM
            frappe.db.get_value('Item', row.ingredient_item, 'stock_uom')
                .then(r => {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'stock_uom', r.message.stock_uom);
                        if (!row.uom) {
                            frappe.model.set_value(cdt, cdn, 'uom', r.message.stock_uom);
                        }
                    }
                });
        }
    },

    qty: function (frm, cdt, cdn) {
        calculate_stock_qty(frm, cdt, cdn);
    },

    uom: function (frm, cdt, cdn) {
        calculate_stock_qty(frm, cdt, cdn);
    }
});

function calculate_stock_qty(frm, cdt, cdn) {
    const row = locals[cdt][cdn];

    if (row.ingredient_item && row.qty && row.uom && row.stock_uom) {
        if (row.uom === row.stock_uom) {
            frappe.model.set_value(cdt, cdn, 'stock_qty', row.qty);
        } else {
            // Get conversion factor
            frappe.call({
                method: 'erpnext.stock.get_item_details.get_conversion_factor',
                args: {
                    item_code: row.ingredient_item,
                    uom: row.uom
                },
                callback: function (r) {
                    if (r.message) {
                        const stock_qty = flt(row.qty) * flt(r.message.conversion_factor);
                        frappe.model.set_value(cdt, cdn, 'stock_qty', stock_qty);
                    }
                }
            });
        }
    }
}

function calculate_total_cost(frm) {
    let total_cost = 0;

    frm.doc.ingredients.forEach(function (ingredient) {
        frappe.db.get_value('Item', ingredient.ingredient_item, 'valuation_rate')
            .then(r => {
                if (r.message) {
                    const cost = flt(ingredient.stock_qty) * flt(r.message.valuation_rate);
                    total_cost += cost;
                }
            });
    });

    setTimeout(function () {
        frappe.msgprint(__('Estimated Cost: {0}', [format_currency(total_cost)]));
    }, 500);
}
