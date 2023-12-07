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
            console.log(this.model);
            if (action) {
                this.actionService.doAction(action);
            }
            // if (result.updated_ids) {
            //     this.model.reload().then(() => {
            //         console.log('View reloaded');
            //     });
            // }

        } catch (error) {
            console.error('Error:', error);
        }
    }
}
