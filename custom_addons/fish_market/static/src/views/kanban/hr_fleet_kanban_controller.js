/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useBus, useService } from "@web/core/utils/hooks";
import { useRef } from "@odoo/owl";

export class HrFleetKanbanController extends KanbanController {
    async OnTestClick() {
        console.log('Hello World');
    }
}
