/** @odoo-module */

import { Product } from "@point_of_sale/app/store/models";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";


patch(Product.prototype, {
	getPricesInOtherCurrencies() {
		const pricelist = this.pos.getDefaultPricelist();

		const basePrice = this.get_price(pricelist, 1.0, 0, true); // Assuming lst_price is the base price in the base currency
		const currencyId = this.pos.currency;
		let pricesInOtherCurrencies = [];

		this.pos.currency_rates.forEach(currency => {
			if (currency.id !== currencyId.id) { // Skip the base currency
				const exchangeRate = currency.rate; // Assuming the currency object has a 'rate' field
				const convertedPrice = basePrice / exchangeRate;
				const formattedPrice = `${currency.symbol} ${convertedPrice.toFixed(2)}`; // Format the price

				pricesInOtherCurrencies.push({
					id: currency.id,
					formattedPrice: formattedPrice
				});
			}
		});
		return pricesInOtherCurrencies;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.pricesInOtherCurrencies = json.pricesInOtherCurrencies || this.getPricesInOtherCurrencies();
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.pricesInOtherCurrencies = this.getPricesInOtherCurrencies();
        return json;
    },
});

patch(PosStore.prototype, {
    async _processData(loadedData) {
		await super._processData(loadedData);
        this.currency_rates = loadedData['currency_rates'];
	},
});
