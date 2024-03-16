/** @odoo-module */

import { ProductsWidget } from "@point_of_sale/app/screens/product_screen/product_list/product_list";
import { patch } from "@web/core/utils/patch";


patch(ProductsWidget.prototype, {
	search_partner(query) {
		this.pos.customer_search_results = [];
		if (query.length >= 2) {
			this.pos.customer_search_results = this.pos.partners.filter(partner => partner.name.includes(query));
		}
	},

	select_customer(pos, customer) {
		pos.get_order().set_partner(customer);
	},

	setup() {
        super.setup(...arguments);
		this.searchCustomerWord;
		this.pos.customer_search_results = [];
    },
});
