/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { CashOpeningPopup } from "@point_of_sale/app/store/cash_opening_popup/cash_opening_popup";
import { PosStore } from "@point_of_sale/app/store/pos_store";
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


patch(ClosePosPopup.prototype, {
    setup() {
        this.cash_pm_id = null
     	super.setup();

        console.log(this.cash_pm_id)
        const initialCashState = { notes: "", payments: {} };
        this.pos.currencies.forEach((currency) => {
            initialCashState.payments[currency.id] = {
                counted: 0,
            };
        });
        this.initialCashState = useState(initialCashState);

    },

    //@override
	getInitialState() {
		const initialState = super.getInitialState();

		this.props.other_payment_methods.forEach((pm) => {
            if (pm.type === "cash") {
                initialState.payments[pm.id] = {
                    counted: this.env.utils.formatCurrency(pm.amount, false),
                };

                this.cash_pm_id = pm.id;
                console.log(this.cash_pm_id)

            }
        });
        return initialState;
    },

    setCashCurrencies(amount) {
        if (!this.env.utils.isValidFloat(amount) || amount == 'NaN' || amount == '') {
            return;
        }
        let total = 0;
        this.pos.currencies.forEach((currency) => {
            total += parseFloat(this.initialCashState.payments[currency.id].counted) / currency.rate;
        });
        this.state.payments[this.props.default_cash_details.id].counted = this.env.utils.formatCurrency(total, false);
    },

    formatCurrency(amount, currency_id) {
        return formatCurrency(parseFloat(amount), currency_id);
    },

    getPosCurrencies() {
        return this.pos.currencies;
    },

    async correct_journals_for_currencies() {
        await this.orm.call(
            "pos.session",
            "correct_cash_amounts",
            [this.pos.pos_session.id],
            {
                cash_amounts_in_currencies: this.initialCashState,
            }
        );
    }
});


patch(PosStore.prototype, {
    async _processData(loadedData) {
		await super._processData(loadedData);
        this.currencies = loadedData['currencies'];
	},
});
