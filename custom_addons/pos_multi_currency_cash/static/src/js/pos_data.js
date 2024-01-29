/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { CashOpeningPopup } from "@point_of_sale/app/store/cash_opening_popup/cash_opening_popup";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ProductsWidget } from "@point_of_sale/app/screens/product_screen/product_list/product_list";
import { Product } from "@point_of_sale/app/store/models";
import { Order, Payment } from "@point_of_sale/app/store/models";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";
import { useErrorHandlers, useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";
import { roundPrecision as round_pr } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";


patch(CashOpeningPopup.prototype, {
    setCashCurrencies(amount) {
        if (!this.env.utils.isValidFloat(amount) || amount == 'NaN' || amount == '') {
            return;
        }
        if (!this.pos.config.cash_control) {
            return;
        }

        let total = 0;
        let default_currency_rate = this.pos.currency.rate;

        this.pos.currencies.forEach((currency) => {
            let currency_rate = default_currency_rate / currency.rate;
            total += parseFloat(currency.counted) / currency_rate;
        });
        this.state.openingCash = this.env.utils.formatCurrency(total, false);
    },

    //@override
	async confirm() {
        this.correct_journals_for_currencies();
        super.confirm();
    },

    async correct_journals_for_currencies() {
        this.pos.currencies.forEach((currency) => {
            currency['counted'] = parseFloat(currency['counted']);
        });

        if (this.pos.config.cash_control && this.pos.currencies.length > 0) {
            await this.orm.call(
                "pos.session",
                "correct_cash_amounts_opening",
                [this.pos.pos_session.id],
                {
                    cash_amounts_in_currencies: this.pos.currencies,
                }
            );
        }
    }
});


patch(ClosePosPopup.prototype, {
    // @override
    setup() {
        super.setup();
        // Used for updating the view
        this.setCashCurrencies('0');
    },

    setCashCurrencies(amount) {
        if (!this.env.utils.isValidFloat(amount) || amount == 'NaN' || amount == '') {
            return;
        }
        if (!this.pos.config.cash_control) {
            return;
        }

        let total = 0;
        let default_currency_rate = this.pos.currency.rate;

        this.pos.currencies.forEach((currency) => {
            let currency_rate = default_currency_rate / currency.rate;
            total += parseFloat(currency.counted) / currency_rate;
        });

        this.state.payments[this.props.default_cash_details.id].counted = this.env.utils.formatCurrency(total, false);
    },

    async correct_journals_for_currencies() {
        if (this.pos.config.cash_control && this.pos.currencies.length > 0) {
            this.pos.currencies.forEach((currency) => {
                currency['counted'] = parseFloat(currency['counted']);
            });

            await this.orm.call(
                "pos.session",
                "correct_cash_amounts_closing",
                [this.pos.pos_session.id],
                {
                    cash_amounts_in_currencies: this.pos.currencies,
                }
            );
        }
    }
});


patch(Product.prototype, {
    getAvailableStock() {
        // console.log('getAvailableStock', this.pos.get_order_list());
		let availableStock = this.pos.available_product_id_quantities[this.id] || 0;
		return availableStock;
	},

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.availableStock = json.availableStock || this.getAvailableStock();
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.availableStock = this.getAvailableStock();
        return json;
    },
});


patch(ProductsWidget.prototype, {
    // @override
	get productsToDisplay() {
        let productsToDisplay = super.productsToDisplay.filter((product) => {
            if (this.pos.available_product_ids.includes(product.id)) {
                return true;
            }
        })
		return productsToDisplay;
    },
});


patch(PosStore.prototype, {
    async _processData(loadedData) {
		await super._processData(loadedData);
        this.currencies = loadedData['currencies'];
        await this._reloadAvailableStock();
	},

    async _reloadAvailableStock() {
        const result = await this.orm.call(
            "pos.session",
            "get_available_product_quantities",
            [this.pos_session.id],
        );
        var available_product_ids = []
        for(var key in result) available_product_ids.push( parseInt(key) );

        this.available_product_ids = available_product_ids;
        this.available_product_id_quantities = result;
    },


    async _save_to_server(orders, options) {
        const result = await super._save_to_server(orders, options);
        await this._reloadAvailableStock();
        return result;
    },


    formatCurrency(amount, currency_id) {
        return formatCurrency(parseFloat(amount), currency_id);
    },
});
