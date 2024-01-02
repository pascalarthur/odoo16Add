/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { CashOpeningPopup } from "@point_of_sale/app/store/cash_opening_popup/cash_opening_popup";
import { PosStore } from "@point_of_sale/app/store/pos_store";
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
	props: ['journal_ids', 'currency_ids'],

	setup() {
		super.setup();

		this.alternative_currency_states = useState(this.get_alternative_currency_states());
	},

	get_alternative_currency_states() {
		let states = [];

		for (const [ii, pm_id] of this.pos.pos_session.payment_method_ids.entries()) {
			let journal_id = this.props.journal_ids[ii];
			let currency_id = this.props.currency_ids[ii];

			if (currency_id != this.pos.currency.id) {
				states.push({
					id: pm_id,
					pm_id: pm_id,
					openingCash: this.env.utils.formatCurrency(0, false),
					currency_id: currency_id,
					journal_id: journal_id,
				});
			}
		}
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
    }
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
			console.log(this.popup);
		}
	}
});

