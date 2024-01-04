/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { CashOpeningPopup } from "@point_of_sale/app/store/cash_opening_popup/cash_opening_popup";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { _t } from "@web/core/l10n/translation";



patch(ClosePosPopup.prototype, {
    //@override
	getInitialState() {
		const initialState = super.getInitialState();

		this.props.other_payment_methods.forEach((pm) => {
            if (pm.type === "cash") {
				console.log(pm.id);
                initialState.payments[pm.id] = {
                    counted: this.env.utils.formatCurrency(pm.amount, false),
                };
            }
        });
		console.log(initialState)
        return initialState;
    },
});

patch(CashOpeningPopup.prototype, {
	props: ['other_payment_methods'],

	setup() {
		super.setup();

		console.log(this.props.other_payment_methods)
		this.alternative_currency_states = useState(this.get_alternative_currency_states());
	},

	get_alternative_currency_states() {
		let states = [];

		this.props.other_payment_methods.forEach(pm => {
			if (pm.type === 'cash' && pm.currency_id != this.pos.currency.id) {
				states.push({
					id: pm.id,
					pm_id: pm.id,
					openingCash: this.env.utils.formatCurrency(0, false),
					currency_id: pm.currency_id,
					currency_name: pm.currency_name,
					journal_id: pm.journal_id,
				});
			}
		})
		return states;
	},

    //@override
	async confirm() {
        this.pos.pos_session.state = "opened";
        this.orm.call("pos.session", "set_cashbox_pos_multi_currency", [
            this.pos.pos_session.id,
			this.alternative_currency_states,
        ]);
        super.confirm();
    },
});

patch(PosStore.prototype, {
	async getOpeningPosInfo() {
		return await this.orm.call("pos.session", "get_opening_control_data", [
            [this.pos_session.id],
        ]);
    },

	// override
	async openCashControl() {
		if (this.shouldShowCashControl()) {
			const info = await this.getOpeningPosInfo();
			this.popup.add(CashOpeningPopup, {...info, keepBehind: true });
		}
	},
});
