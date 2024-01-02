/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { CashOpeningPopup } from "@point_of_sale/app/store/cash_opening_popup/cash_opening_popup";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";


patch(ClosePosPopup.prototype, {
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
});

patch(CashOpeningPopup.prototype, {
	setup() {
		super.setup();

		let states = this.get_alternative_currency_states();
		this.alternative_currency_states = useState(states);
	},

	get_alternative_currency_states() {
		let states = {};
		this.pos.poscurrency.forEach(currency => {
			if (currency.id != this.pos.currency.id) {
				states[currency.id] = useState({
					notes: "",
					openingCash: 0.0
				});
			}

		});
		return states;
	},

    //@override
	async confirm() {
        this.pos.pos_session.state = "opened";
		console.log(this.alternative_currency_states)
        this.orm.call("pos.session", "set_cashbox_pos_multi_currency", [
            this.pos.pos_session.id,
			this.alternative_currency_states,
        ]);
        super.confirm();
    }
});