/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { PosStore } from "@point_of_sale/app/store/pos_store";


patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.invoice_auto_check) {
            // Check if a customer is selected for the current order
            if (this.currentOrder.get_partner()) {
                this.currentOrder.set_to_invoice(true);
            }
        }
    },
    async _isOrderValid(isForceValidate) {
        var valid = await super._isOrderValid(isForceValidate)
        console.log('isOrderValid', this.currentOrder.to_invoice)
        if (this.pos.invoice_auto_check && this.currentOrder.get_partner() != null && !this.currentOrder.to_invoice) {
            console.log("Invoice auto check is enabled, setting to_invoice to true")
            return false;
        }
        return valid;
    },
});

patch(PosStore.prototype, {
    async _processData(loadedData) {
		await super._processData(loadedData);
        this.invoice_auto_check = loadedData['invoice_auto_check'];
	},
});
