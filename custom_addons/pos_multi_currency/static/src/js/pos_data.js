/** @odoo-module */

import { Product } from "@point_of_sale/app/store/models";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";


patch(Product.prototype, {
	getPricesInOtherCurrencies() {
		const pricelist = this.pos.getDefaultPricelist();
		const basePrice = this.get_price(pricelist, 1.0, 0, true); // Assuming lst_price is the base price in the base currency
		let pricesInOtherCurrencies = [];

		this.pos.currency_rates.forEach(currency => {
			if (currency.id !== this.pos.currency.id) { // Skip the base currency
				const convertedPrice = basePrice / currency.rate;
				const formattedPrice = `${convertedPrice.toFixed(2)} ${currency.symbol}`; // Format the price

				pricesInOtherCurrencies.push({
					id: currency.id,
					formattedPrice: formattedPrice
				});
			}
		});
		return pricesInOtherCurrencies;
    },
});

patch(PosStore.prototype, {
    async _processData(loadedData) {
		await super._processData(loadedData);
        this.currency_rates = loadedData['currency_rates'];
	},
});
