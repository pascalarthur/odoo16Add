/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { booleanField, BooleanField } from "@web/views/fields/boolean/boolean_field";

class CheckboxWidget extends BooleanField {
    static props = {
        ...BooleanField.props,
        autosave: { type: Boolean, optional: true },
    };

    async onChange(newValue) {
        this.state.value = newValue;
        const changes = { [this.props.name]: newValue };
        await this.props.record.update(changes, { save: this.props.autosave });
    }
}

export const checkboxWidget = {
    ...booleanField,
    component: CheckboxWidget,
    displayName: _t("Toggle"),
    supportedOptions: [
        {
            label: _t("Autosave"),
            name: "autosave",
            type: "boolean",
            default: true,
            help: _t(
                "If checked, the record will be saved immediately when the field is modified."
            ),
        },
    ],
    extractProps({ options }, dynamicInfo) {
        return {
            autosave: "autosave" in options ? Boolean(options.autosave) : true,
            readonly: dynamicInfo.readonly,
        };
    },
};
registry.category("fields").add("custom_checkbox_widget", checkboxWidget);
