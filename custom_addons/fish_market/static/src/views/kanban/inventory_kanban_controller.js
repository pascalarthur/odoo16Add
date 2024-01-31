/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useBus, useService } from "@web/core/utils/hooks";
import { useRef } from "@odoo/owl";


export class InventoryKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.rpc = useService('rpc');
        this.actionService = useService('action');
    }

    async OnTestClick() {
        try {
            const action = await this.rpc("/fish_market/sell_selected_products");
            if (action) {
                this.actionService.doAction(action, {
                    additional_context: {
                        'form_view_initial_mode': 'edit',
                    },
                    on_close: () => {
                        console.log('Deleting content');
                        this.rpc({
                            model: 'sale.order',
                            method: 'check_and_delete_order',
                            args: [action.res_id, action.context.default_create_date],
                        });
                    }
                });
            }

        } catch (error) {
            console.error('Error:', error);
        }
    }

    async ConvertDamagedProducts() {
        try {
            const action = await this.rpc("/fish_market/process_damaged_products");
            if (action) {
                this.actionService.doAction(action, {
                    additional_context: {
                        'form_view_initial_mode': 'edit',
                    },
                });
            }

        } catch (error) {
            console.error('Error:', error);
        }
    }
}
