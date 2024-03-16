# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class PosSession(models.Model):
    _inherit = "pos.session"

    POS_SESSION_STATE = [
        ("opening_control", "Opening Control"),  # method action_pos_session_open
        ("opened", "In Progress"),  # method action_pos_session_closing_control
        ("closing_control", "Closing Control"),  # method action_pos_session_close
        ("closed", "Closed & Posted"),
        ("cancel", "Cancel"),
    ]  # method sh_session_cancel
    state = fields.Selection(
        POS_SESSION_STATE,
        string="Status",
        required=True,
        readonly=True,
        index=True,
        copy=False,
        default="opening_control",
    )

    @api.constrains("config_id")
    def _check_pos_config(self):
        if (
            self.search_count(
                [
                    ("state", "not in", ["closed", "cancel"]),
                    ("config_id", "=", self.config_id.id),
                    ("rescue", "=", False),
                ]
            )
            > 1
        ):
            raise ValidationError(
                _("Another session is already opened for this point of sale.")
            )

    def sh_session_cancel(self):
        for rec in self:
            if rec.state == 'closed':                
                # ================Delete Session====================
                if rec.company_id.sh_pos_operation_type == "cancel_delete":
                    # =========Pos Payment Delete=============
                    self._cr.execute(
                        """
                        select id from pos_payment where session_id = %s """,
                        [rec.id],
                    )
                    payments = self._cr.dictfetchall()
                    if payments:
                        payments = self.env["pos.payment"].browse(
                                [r["id"] for r in payments]
                            )
                        for pay in payments:
                            pay.unlink()

                    # ================== Journal Item Delete==============
                    all_related_moves = rec._get_related_account_moves()
                    if all_related_moves:
                        if all_related_moves.mapped("line_ids") or all_related_moves.mapped(
                            "line_ids"
                        ).mapped("analytic_line_ids"):
                            self._cr.execute(
                                """ DELETE FROM account_partial_reconcile WHERE debit_move_id IN %s or credit_move_id IN %s""",
                                [
                                    tuple(
                                        all_related_moves.mapped("line_ids").ids
                                        + all_related_moves.mapped("line_ids")
                                        .mapped("analytic_line_ids")
                                        .ids
                                    ),
                                    tuple(
                                        all_related_moves.mapped("line_ids").ids
                                        + all_related_moves.mapped("line_ids")
                                        .mapped("analytic_line_ids")
                                        .ids
                                    ),
                                ],
                            )
                            self._cr.execute(
                                """ DELETE FROM account_move_line WHERE id IN %s""",
                                [
                                    tuple(
                                        all_related_moves.mapped("line_ids").ids
                                        + all_related_moves.mapped("line_ids")
                                        .mapped("analytic_line_ids")
                                        .ids
                                    )
                                ],
                            )
                        self._cr.execute(
                            """ DELETE FROM account_move WHERE id IN %s """,
                            [tuple(all_related_moves.ids)],
                        )

                    # ================= Account Bank Statement ===========
                    self._cr.execute(
                        """ DELETE FROM account_bank_statement_line WHERE pos_session_id = %s""",
                        [rec.id],
                    )

                    # =========Pos Order Delete=============
                    self._cr.execute(
                        """
                        select id from pos_order where session_id = %s """,
                        [rec.id],
                    )
                    orders = self._cr.dictfetchall()
                    if orders:
                        # =========Pos Stock Delete=============
                        self._cr.execute(
                            """select id from stock_picking where pos_session_id=%s """,
                            [rec.id],
                        )
                        picking = self._cr.dictfetchall()
                        if picking:
                            self._cr.execute(
                                """select id from stock_move where picking_id IN %s """,
                                [tuple([r["id"] for r in picking])],
                            )
                            moves = self._cr.dictfetchall()
                            self._cr.execute(
                                """select id from stock_move_line where picking_id IN %s """,
                                [tuple([r["id"] for r in picking])],
                            )
                            move_lines = self._cr.dictfetchall()
                            movelines = self.env["stock.move.line"].browse(
                                [r["id"] for r in move_lines]
                            )
                            for line in movelines:
                                print("\n\n\n\n\n\n =========== Lineee", line)
                                quant = (
                                    self.env["stock.quant"]
                                    .sudo()
                                    .search(
                                        [
                                            ("location_id", "=", line.location_id.id),
                                            ("product_id", "=", line.product_id.id),
                                            ("lot_id", "=", line.lot_id.id),
                                        ],
                                        limit=1,
                                    )
                                )
                                if quant:
                                    quant.write(
                                        {"quantity": quant.quantity + line.quantity}
                                    )
                                quant = (
                                    self.env["stock.quant"]
                                    .sudo()
                                    .search(
                                        [
                                            ("location_id", "=", line.location_dest_id.id),
                                            ("product_id", "=", line.product_id.id),
                                            ("lot_id", "=", line.lot_id.id),
                                        ],
                                        limit=1,
                                    )
                                )
                                if quant:
                                    quant.write(
                                        {"quantity": quant.quantity - line.quantity}
                                    )
                            self._cr.execute(
                                """ DELETE FROM stock_move_line WHERE id IN %s""",
                                [tuple(movelines.ids)],
                            )
                            self._cr.execute(
                                """ DELETE FROM stock_move WHERE id IN %s""",
                                [tuple([r["id"] for r in moves])],
                            )
                            self._cr.execute(
                                """ DELETE FROM stock_picking WHERE id IN %s""",
                                [tuple([r["id"] for r in picking])],
                            )
                        self._cr.execute(
                            """ DELETE FROM pos_order WHERE id IN %s """,
                            [tuple([r["id"] for r in orders])],
                        )

                    # =========Pos Session Delete=============
                    self._cr.execute(
                        """ DELETE FROM pos_session WHERE id = %s """, [rec.id]
                    )
                    return {
                    'name': 'POS Session',
                    'type': 'ir.actions.act_window',
                    'res_model': 'pos.session',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'target': 'current',
                    }

                # ================Cancel Session====================

                elif rec.company_id.sh_pos_operation_type == "cancel":
                    # =========Pos Payment Delete=============
                    self._cr.execute(
                        """
                        select id from pos_payment where session_id = %s """,
                        [rec.id],
                    )
                    payments = self._cr.dictfetchall()
                    if payments:
                        payments = self.env["pos.payment"].browse(
                                [r["id"] for r in payments]
                            )
                        for pay in payments:
                            pay.unlink()
                      
                    # ================== Journal Item Delete==============
                    all_related_moves = rec._get_related_account_moves()
                    if all_related_moves:
                        if all_related_moves.mapped("line_ids") or all_related_moves.mapped(
                            "line_ids"
                        ).mapped("analytic_line_ids"):
                            self._cr.execute(
                                """ DELETE FROM account_partial_reconcile WHERE debit_move_id IN %s or credit_move_id IN %s""",
                                [
                                    tuple(all_related_moves.mapped("line_ids").ids),
                                    tuple(all_related_moves.mapped("line_ids").ids),
                                ],
                            )
                            self._cr.execute(
                                """ DELETE FROM account_move_line WHERE id IN %s""",
                                [tuple(all_related_moves.mapped("line_ids").ids)],
                            )
                        self._cr.execute(
                            """ UPDATE account_move set state='cancel' WHERE id IN %s """,
                            [tuple(all_related_moves.ids)],
                        )

                    # ================= Account Bank Statement ===========
                    self._cr.execute(
                        """ DELETE FROM account_bank_statement_line WHERE pos_session_id = %s""",
                        [rec.id],
                    )

                    # =========Pos Order Delete=============
                    self._cr.execute(
                        """
                        select id from pos_order where session_id = %s """,
                        [rec.id],
                    )
                    orders = self._cr.dictfetchall()
                    if orders:

                        # =========Pos Stock Delete=============
                        self._cr.execute(
                            """select id from stock_picking where pos_session_id=%s """,
                            [rec.id],
                        )
                        picking = self._cr.dictfetchall()
                        if picking:
                            self._cr.execute(
                                """select id from stock_move where picking_id IN %s """,
                                [tuple([r["id"] for r in picking])],
                            )
                            moves = self._cr.dictfetchall()
                            self._cr.execute(
                                """select id from stock_move_line where picking_id IN %s """,
                                [tuple([r["id"] for r in picking])],
                            )
                            move_lines = self._cr.dictfetchall()
                            movelines = self.env["stock.move.line"].browse(
                                [r["id"] for r in move_lines]
                            )
                            for line in movelines:
                                print("\n\n\n\n\n\n ====02======= Lineee", line)
                                quant = (
                                    self.env["stock.quant"]
                                    .sudo()
                                    .search(
                                        [
                                            ("location_id", "=", line.location_id.id),
                                            ("product_id", "=", line.product_id.id),
                                            ("lot_id", "=", line.lot_id.id),
                                        ],
                                        limit=1,
                                    )
                                )
                                if quant:
                                    quant.write(
                                        {"quantity": quant.quantity + line.quantity}
                                    )
                                quant = (
                                    self.env["stock.quant"]
                                    .sudo()
                                    .search(
                                        [
                                            ("location_id", "=", line.location_dest_id.id),
                                            ("product_id", "=", line.product_id.id),
                                            ("lot_id", "=", line.lot_id.id),
                                        ],
                                        limit=1,
                                    )
                                )
                                if quant:
                                    quant.write(
                                        {"quantity": quant.quantity - line.quantity}
                                    )
                            self._cr.execute(
                                """ UPDATE stock_move set state='cancel' WHERE id IN %s """,
                                [tuple([r["id"] for r in moves])],
                            )
                            self._cr.execute(
                                """ UPDATE stock_picking set state='cancel' WHERE id IN %s """,
                                [tuple([r["id"] for r in picking])],
                            )
                        self._cr.execute(
                            """ UPDATE pos_order set state='cancel' WHERE id IN %s """,
                            [tuple([r["id"] for r in orders])],
                        )

                    # =========Pos Session Delete=============
                    self._cr.execute(
                        """ UPDATE pos_session set state='cancel' WHERE id = %s """,
                        [rec.id],
                    )
                    
                    
                    
    def sh_mass_session_delete(self):
        if self.env.context and self.env.context.get('active_ids'):
            for session in self.env.context.get('active_ids'):
                rec=self.env['pos.session'].search([('id','=',session)])
                if rec:
                    if rec.state == 'closed':                
                        # ================Delete Session====================
                        # =========Pos Payment Delete=============
                        self._cr.execute(
                            """
                            select id from pos_payment where session_id = %s """,
                            [rec.id],
                        )
                        payments = self._cr.dictfetchall()
                        if payments:
                            payments = self.env["pos.payment"].browse(
                                    [r["id"] for r in payments]
                                )
                            for pay in payments:
                                pay.unlink()

                        # ================== Journal Item Delete==============
                        all_related_moves = rec._get_related_account_moves()
                        if all_related_moves:
                            if all_related_moves.mapped("line_ids") or all_related_moves.mapped(
                                "line_ids"
                            ).mapped("analytic_line_ids"):
                                self._cr.execute(
                                    """ DELETE FROM account_partial_reconcile WHERE debit_move_id IN %s or credit_move_id IN %s""",
                                    [
                                        tuple(
                                            all_related_moves.mapped("line_ids").ids
                                            + all_related_moves.mapped("line_ids")
                                            .mapped("analytic_line_ids")
                                            .ids
                                        ),
                                        tuple(
                                            all_related_moves.mapped("line_ids").ids
                                            + all_related_moves.mapped("line_ids")
                                            .mapped("analytic_line_ids")
                                            .ids
                                        ),
                                    ],
                                )
                                self._cr.execute(
                                    """ DELETE FROM account_move_line WHERE id IN %s""",
                                    [
                                        tuple(
                                            all_related_moves.mapped("line_ids").ids
                                            + all_related_moves.mapped("line_ids")
                                            .mapped("analytic_line_ids")
                                            .ids
                                        )
                                    ],
                                )
                            self._cr.execute(
                                """ DELETE FROM account_move WHERE id IN %s """,
                                [tuple(all_related_moves.ids)],
                            )

                        # ================= Account Bank Statement ===========
                        self._cr.execute(
                            """ DELETE FROM account_bank_statement_line WHERE pos_session_id = %s""",
                            [rec.id],
                        )
                        # =========Pos Order Delete=============
                        self._cr.execute(
                            """
                            select id from pos_order where session_id = %s """,
                            [rec.id],
                        )
                        orders = self._cr.dictfetchall()
                        if orders:
                            # =========Pos Stock Delete=============
                            self._cr.execute(
                                """select id from stock_picking where pos_session_id=%s """,
                                [rec.id],
                            )
                            picking = self._cr.dictfetchall()
                            if picking:
                                self._cr.execute(
                                    """select id from stock_move where picking_id IN %s """,
                                    [tuple([r["id"] for r in picking])],
                                )
                                moves = self._cr.dictfetchall()
                                self._cr.execute(
                                    """select id from stock_move_line where picking_id IN %s """,
                                    [tuple([r["id"] for r in picking])],
                                )
                                move_lines = self._cr.dictfetchall()
                                movelines = self.env["stock.move.line"].browse(
                                    [r["id"] for r in move_lines]
                                )
                                for line in movelines:
                                    print("\n\n\n\n\n\n ====03======= Lineee", line)
                                    quant = (
                                        self.env["stock.quant"]
                                        .sudo()
                                        .search(
                                            [
                                                ("location_id", "=", line.location_id.id),
                                                ("product_id", "=", line.product_id.id),
                                                ("lot_id", "=", line.lot_id.id),
                                            ],
                                            limit=1,
                                        )
                                    )
                                    if quant:
                                        quant.write(
                                            {"quantity": quant.quantity + line.quantity}
                                        )
                                    quant = (
                                        self.env["stock.quant"]
                                        .sudo()
                                        .search(
                                            [
                                                ("location_id", "=", line.location_dest_id.id),
                                                ("product_id", "=", line.product_id.id),
                                                ("lot_id", "=", line.lot_id.id),
                                            ],
                                            limit=1,
                                        )
                                    )
                                    if quant:
                                        quant.write(
                                            {"quantity": quant.quantity - line.quantity}
                                        )
                                self._cr.execute(
                                    """ DELETE FROM stock_move_line WHERE id IN %s""",
                                    [tuple(movelines.ids)],
                                )
                                self._cr.execute(
                                    """ DELETE FROM stock_move WHERE id IN %s""",
                                    [tuple([r["id"] for r in moves])],
                                )
                                self._cr.execute(
                                    """ DELETE FROM stock_picking WHERE id IN %s""",
                                    [tuple([r["id"] for r in picking])],
                                )
                            self._cr.execute(
                                """ DELETE FROM pos_order WHERE id IN %s """,
                                [tuple([r["id"] for r in orders])],
                            )

                        # =========Pos Session Delete=============
                        self._cr.execute(
                            """ DELETE FROM pos_session WHERE id = %s """, [rec.id]
                        )
                        # ================Cancel Session====================
                        
    def sh_mass_session_cancel(self):
        if self.env.context and self.env.context.get('active_ids'):
            for session in self.env.context.get('active_ids'):
                rec=self.env['pos.session'].search([('id','=',session)])
                if rec:
                    if rec.state == 'closed':
                        # =========Pos Payment Delete=============
                        self._cr.execute(
                            """
                            select id from pos_payment where session_id = %s """,
                            [rec.id],
                        )
                        payments = self._cr.dictfetchall()
                        if payments:
                            payments = self.env["pos.payment"].browse(
                                    [r["id"] for r in payments]
                                )
                            for pay in payments:
                                pay.unlink()
                        
                        # ================== Journal Item Delete==============
                        all_related_moves = rec._get_related_account_moves()
                        if all_related_moves:
                            if all_related_moves.mapped("line_ids") or all_related_moves.mapped(
                                "line_ids"
                            ).mapped("analytic_line_ids"):
                                self._cr.execute(
                                    """ DELETE FROM account_partial_reconcile WHERE debit_move_id IN %s or credit_move_id IN %s""",
                                    [
                                        tuple(all_related_moves.mapped("line_ids").ids),
                                        tuple(all_related_moves.mapped("line_ids").ids),
                                    ],
                                )
                                self._cr.execute(
                                    """ DELETE FROM account_move_line WHERE id IN %s""",
                                    [tuple(all_related_moves.mapped("line_ids").ids)],
                                )
                            self._cr.execute(
                                """ UPDATE account_move set state='cancel' WHERE id IN %s """,
                                [tuple(all_related_moves.ids)],
                            )

                        ## ================= Account Bank Statement ===========
                        self._cr.execute(
                            """ DELETE FROM account_bank_statement_line WHERE pos_session_id = %s""",
                            [rec.id],
                        )

                        # =========Pos Order Delete=============
                        self._cr.execute(
                            """
                            select id from pos_order where session_id = %s """,
                            [rec.id],
                        )
                        orders = self._cr.dictfetchall()
                        if orders:

                            # =========Pos Stock Delete=============
                            self._cr.execute(
                                """select id from stock_picking where pos_session_id=%s """,
                                [rec.id],
                            )
                            picking = self._cr.dictfetchall()
                            if picking:
                                self._cr.execute(
                                    """select id from stock_move where picking_id IN %s """,
                                    [tuple([r["id"] for r in picking])],
                                )
                                moves = self._cr.dictfetchall()
                                self._cr.execute(
                                    """select id from stock_move_line where picking_id IN %s """,
                                    [tuple([r["id"] for r in picking])],
                                )
                                move_lines = self._cr.dictfetchall()
                                movelines = self.env["stock.move.line"].browse(
                                    [r["id"] for r in move_lines]
                                )
                                for line in movelines:
                                    print("\n\n\n\n\n\n =====04====== Lineee", line)
                                    quant = (
                                        self.env["stock.quant"]
                                        .sudo()
                                        .search(
                                            [
                                                ("location_id", "=", line.location_id.id),
                                                ("product_id", "=", line.product_id.id),
                                                ("lot_id", "=", line.lot_id.id),
                                            ],
                                            limit=1,
                                        )
                                    )
                                    if quant:
                                        quant.write(
                                            {"quantity": quant.quantity + line.quantity}
                                        )
                                    quant = (
                                        self.env["stock.quant"]
                                        .sudo()
                                        .search(
                                            [
                                                ("location_id", "=", line.location_dest_id.id),
                                                ("product_id", "=", line.product_id.id),
                                                ("lot_id", "=", line.lot_id.id),
                                            ],
                                            limit=1,
                                        )
                                    )
                                    if quant:
                                        quant.write(
                                            {"quantity": quant.quantity - line.quantity}
                                        )
                                self._cr.execute(
                                    """ UPDATE stock_move set state='cancel' WHERE id IN %s """,
                                    [tuple([r["id"] for r in moves])],
                                )
                                self._cr.execute(
                                    """ UPDATE stock_picking set state='cancel' WHERE id IN %s """,
                                    [tuple([r["id"] for r in picking])],
                                )
                            self._cr.execute(
                                """ UPDATE pos_order set state='cancel' WHERE id IN %s """,
                                [tuple([r["id"] for r in orders])],
                            )

                        # =========Pos Session Delete=============
                        self._cr.execute(
                            """ UPDATE pos_session set state='cancel' WHERE id = %s """,
                            [rec.id],
                        )
