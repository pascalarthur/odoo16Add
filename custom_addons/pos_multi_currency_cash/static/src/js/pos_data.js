/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";


patch(ClosePosPopup.prototype, {
	setup() {
		super.setup();
		this.alternative_currencies = this.getPricesInOtherCurrencies();
	},

    //@override
	getInitialState() {
		const initialState = super.getInitialState();

		this.props.other_payment_methods.forEach((pm) => {
            if (pm.type === "cash") {
                initialState.payments[pm.id] = {
                    counted: this.env.utils.formatCurrency(pm.amount, false),
                };
            }
        });
		console.log(initialState)
        return initialState;
    },

	getPricesInOtherCurrencies() {
		let alternative_currencies = [];
		const currencyId = this.pos.currency;
		const currencies = this.pos.poscurrency;

		console.log(this.pos);
		console.log(this.props.other_payment_methods);

		currencies.forEach(currency => {
			if (currency.id !== currencyId.id) { // Skip the base currency
				alternative_currencies.push({
					id: currency.id,
					name: currency.name
				});
			}
		});
		return alternative_currencies;
    },
});