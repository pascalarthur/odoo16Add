/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { InventoryKanbanController } from "@fish_market/views/kanban/inventory_kanban_controller";

export const InventoryFleetKanbanView = {
    ...kanbanView,
    Controller: InventoryKanbanController,
    buttonTemplate: "fish_market.KanbanController.Buttons",
};
registry.category("views").add("inventory_kanban_view", InventoryFleetKanbanView);
