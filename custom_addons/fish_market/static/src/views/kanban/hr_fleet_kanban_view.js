/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { HrFleetKanbanController } from "@fish_market/views/kanban/hr_fleet_kanban_controller";

export const hrFleetKanbanView = {
    ...kanbanView,
    Controller: HrFleetKanbanController,
    buttonTemplate: "fish_market.KanbanController.Buttons",
};
registry.category("views").add("hr_fleet_kanban_view_2", hrFleetKanbanView);
