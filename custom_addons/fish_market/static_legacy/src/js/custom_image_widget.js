// odoo.define('fish_market.custom_image_widget', function (require) {
//     "use strict";

//     var AbstractField = require('web.AbstractField');
//     var fieldRegistry = require('web.field_registry');

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

//     fieldRegistry.add('custom_image', CustomImageWidget);

//     return CustomImageWidget;
// });


/** @odoo-module **/

// import { _t } from "@web/core/l10n/translation";
// import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
// import { registry } from "@web/core/registry";
// import { FormController } from "@web/views/form/form_controller";
// import { formView } from "@web/views/form/form_view";

export class FleetFormController extends FormController {
    /**
     * @override
     **/
    getStaticActionMenuItems() {
        const list = this.model.root;
        const isM2MGrouped = list.groupBy.some((groupBy) => {
            const fieldName = groupBy.split(":")[0];
            return list.fields[fieldName].type === "many2many";
        });
        return {
            export: {
                isAvailable: () => this.isExportEnable,
                sequence: 10,
                icon: "fa fa-upload",
                description: _t("Export"),
                callback: () => this.onExportData(),
            },
            archive: {
                isAvailable: () => this.archiveEnabled && !isM2MGrouped,
                sequence: 20,
                icon: "oi oi-archive",
                description: _t("Archive"),
                callback: () => {
                    this.dialogService.add(ConfirmationDialog, this.archiveDialogProps);
                },
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled && !isM2MGrouped,
                sequence: 30,
                icon: "oi oi-unarchive",
                description: _t("Unarchive"),
                callback: () => this.toggleArchiveState(false),
            },
            duplicate: {
                isAvailable: () => this.activeActions.duplicate && !isM2MGrouped,
                sequence: 35,
                icon: "fa fa-trash-o",
                description: _t("Custom Duplicate"),
                callback: () => this.duplicateRecords(),
            },
            delete: {
                isAvailable: () => this.activeActions.delete && !isM2MGrouped,
                sequence: 40,
                icon: "fa fa-trash-o",
                description: _t("Delete"),
                callback: () => this.onDeleteSelectedRecords(),
            },
        };
    }
}

export const fleetFormView = {
    ...formView,
    Controller: FleetFormController,
};

registry.category("views").add("custom_image", fleetFormView);
