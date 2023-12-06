/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export class FleetFormController extends FormController {
    /**
     * @override
     **/
    getStaticActionMenuItems() {
        // console.log(super.actionMenuItems());
        const menuItems = super.getStaticActionMenuItems();

        menuItems.duplicate.callback = () => {
            const dialogProps = {
                body: _t(
                    "Every service and contract of this vehicle will be considered as archived. Are you sure that you want to archive this record?"
                ),
                confirm: () => this.model.root.archive(),
                cancel: () => {},
            };
            this.dialogService.add(ConfirmationDialog, dialogProps);
        };
        return menuItems;
    }
}

export const fleetFormView = {
    ...formView,
    Controller: FleetFormController,
};

registry.category("views").add("fish_form", fleetFormView);

// odoo.define('fish_market.custom_image_widget', function (require) {
//     "use strict";

//     var AbstractField = require('web.AbstractField');

//     var CustomImageWidget = AbstractField.extend({
//         // Custom widget code
//         _render: function () {
//             console.log('Hello World');
//             this.$el.empty();
//             if (this.value) {
//                 var imgSrc = 'data:image/png;base64,' + this.value;
//                 var $img = $('<img/>', {src: imgSrc, style: 'max-width:10%;'});
//                 this.$el.append($img);
//             }
//         },
//     });

//     registry.category("fields").add("custom_image", CustomImageWidget);

//     return CustomImageWidget;
// });
