/** @odoo-module */

import { Orderline } from "@point_of_sale/app/store/models";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";


patch(PosStore.prototype, {
    async _processData(loadedData) {
		await super._processData(loadedData);
        this.use_absolute_discount = loadedData['use_absolute_discount'];
	},
}),


patch(ProductScreen.prototype, {
    getNumpadButtons() {
        var buttons = super.getNumpadButtons();
        var discount_button = buttons.find(button => button.value === 'discount');
        if (this.pos.use_absolute_discount) {
            discount_button.text = _t("A. Disc");
        }
        return buttons
    },

    _setValue(val) {
        const { numpadMode } = this.pos;
        const selectedLine = this.currentOrder.get_selected_orderline();
        if (selectedLine) {
            if (numpadMode === "quantity") {
                if (val === "remove") {
                    this.currentOrder.removeOrderline(selectedLine);
                } else {
                    const result = selectedLine.set_quantity(val);
                    if (!result) {
                        this.numberBuffer.reset();
                    }
                }
            } else if (numpadMode === "discount") {
                if (this.pos.use_absolute_discount) {
                    let discount_val = ((val / selectedLine.get_display_price_one()) * 100);
                    selectedLine.set_discount(discount_val);
                }
                else {
                    selectedLine.set_discount(val);
                }


            } else if (numpadMode === "price") {
                selectedLine.price_type = "manual";
                selectedLine.set_unit_price(val);
            }
        }
    },
});


patch(Orderline.prototype, {
    get_discount_str() {
        let total_price = 0.0
        let discount_val = 0.0
        if (this.get_discount() >= 100) {
            discount_val = this.get_unit_price();
        }
        else {
            total_price = this.get_display_price_one() / (1.0 - this.get_discount() / 100.0);
            discount_val = ((this.discount * total_price) / 100);
        }

        console.log("get_discount_str 2", discount_val)

        return this.env.utils.formatCurrency(discount_val) + " / " + this.discount.toFixed(4) + " ";
    },
});