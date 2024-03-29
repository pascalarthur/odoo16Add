/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";


patch(PosStore.prototype, {
	async _processData(loadedData) {
		await super._processData(loadedData);
		this.invoice_auto_check = loadedData['invoice_auto_check'];

        console.log(this);

		this.customer_details = loadedData['customer_details'];
        this.mobile = loadedData['customer_mobile'];
        this.phone = loadedData['customer_phone'];
        this.email = loadedData['customer_email'];
        this.vat = loadedData['customer_vat'];
        this.address = loadedData['customer_address'];
        this.name = loadedData['customer_name'];
	},
});
