/** @odoo-module */

import { Orderline } from "@point_of_sale/app/store/models";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";


patch(Orderline.prototype, {
    set_quantity(quantity, keep_price) {
        if (quantity > this.pos.available_product_id_quantities[this.product.id]) {
            quantity = this.pos.available_product_id_quantities[this.product.id];
        }
        return super.set_quantity(quantity, keep_price);
    },
});