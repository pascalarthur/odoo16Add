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


patch(CashOpeningPopup.prototype, {
	props: ['other_payment_methods'],

	setup() {
		super.setup();
		this.alternative_currency_states = useState(this.get_alternative_currency_states());
	},

	get_alternative_currency_states() {
		let states = [];

		this.props.other_payment_methods.forEach(pm => {
			console.log(pm);
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

patch(PaymentScreenPaymentLines.prototype, {
	//@override
	formatLineAmount(pm) {
		return formatCurrency(pm.get_amount(), pm.payment_method.currency_id);
	},
});

// patch(PaymentScreen.prototype, {

// });


patch(Order.prototype, {
	get_total_paid() {
        return round_pr(
            this.paymentlines.reduce(function (sum, paymentLine) {
                if (paymentLine.is_done()) {
                    sum += paymentLine.get_amount() * paymentLine.payment_method.currency_rate;
                }
                return sum;
            }, 0),
            this.pos.currency.rounding
        );
    },

	get_change(paymentline) {
        if (!paymentline) {
            var change =
                this.get_total_paid() - this.get_total_with_tax() - this.get_rounding_applied();
        } else {
            change = -this.get_total_with_tax();
            var lines = this.paymentlines;
            for (var i = 0; i < lines.length; i++) {
                change += lines[i].get_amount() * lines[i].payment_method.currency_rate;
                if (lines[i] === paymentline) {
                    break;
                }
            }
        }
        return round_pr(Math.max(0, change), this.pos.currency.rounding);
    },

    get_due(paymentline) {
        if (!paymentline) {
            var due =
                this.get_total_with_tax() - this.get_total_paid() + this.get_rounding_applied();
        } else {
            due = this.get_total_with_tax();
            var lines = this.paymentlines;
            for (var i = 0; i < lines.length; i++) {
                if (lines[i] === paymentline) {
                    break;
                } else {
                    due -= lines[i].get_amount() * lines[i].payment_method.currency_rate;
                }
            }
        }
        return round_pr(due, this.pos.currency.rounding);
    }
});
