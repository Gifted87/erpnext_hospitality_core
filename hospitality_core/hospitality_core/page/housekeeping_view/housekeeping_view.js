frappe.pages['housekeeping-view'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Housekeeping Board',
        single_column: true
    });

    // Refresh Button
    page.set_primary_action('Refresh', function () {
        render_housekeeping_board(wrapper);
    });

    $(wrapper).find('.layout-main-section').append('<div id="hk-board-container" class="row"></div>');

    render_housekeeping_board(wrapper);
}

function render_housekeeping_board(wrapper) {
    frappe.call({
        method: "hospitality_core.hospitality_core.page.housekeeping_view.housekeeping_view.get_room_statuses",
        callback: function (r) {
            if (r.message) {
                let container = $('#hk-board-container');
                container.empty();

                r.message.forEach(room => {
                    let card_color = '';
                    if (room.status === 'Dirty') card_color = 'border-danger';
                    else if (room.status === 'Occupied') card_color = 'border-primary';
                    else if (room.status === 'Available') card_color = 'border-success'; // Clean
                    else if (room.status === 'Out of Order') card_color = 'border-secondary';

                    let html = `
                    <div class="col-xs-6 col-sm-4 col-md-3 col-lg-2" style="padding: 10px;">
                        <div class="card ${card_color}" style="border-width: 2px; height: 100%;">
                            <div class="card-body text-center">
                                <h4 class="card-title">${room.room_number}</h4>
                                <p class="card-text text-muted">${room.status}</p>
                                ${get_action_buttons(room)}
                            </div>
                        </div>
                    </div>`;
                    container.append(html);
                });
            }
        }
    });
}

function get_action_buttons(room) {
    // Logic: 
    // Dirty -> Click to make Clean (Available)
    // Clean (Available) -> Click to make Dirty (e.g. inspection fail)
    // Occupied -> Cannot change status here (Must check out)

    if (room.status === 'Dirty') {
        return `<button class="btn btn-success btn-xs btn-block" onclick="update_room_status('${room.name}', 'Available')">Mark Clean</button>`;
    } else if (room.status === 'Available') {
        return `<button class="btn btn-warning btn-xs btn-block" onclick="update_room_status('${room.name}', 'Dirty')">Mark Dirty</button>`;
    } else if (room.status === 'Occupied') {
        // Allow marking occupied rooms as dirty (for daily service)
        return `<button class="btn btn-warning btn-xs btn-block" onclick="update_room_status('${room.name}', 'Dirty')">Mark Dirty</button>`;
    } else {
        return `<small class="text-muted">Locked</small>`;
    }
}

// Global scope function for onclick
window.update_room_status = function (room_name, new_status) {
    frappe.call({
        method: "hospitality_core.hospitality_core.page.housekeeping_view.housekeeping_view.set_room_status",
        args: {
            room: room_name,
            status: new_status
        },
        callback: function (r) {
            // Reload page to reflect changes
            frappe.pages['housekeeping-view'].get_primary_action().trigger('click');
        }
    });
};