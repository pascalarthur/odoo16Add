from odoo import models, fields, api, _, exceptions

class IntercompanyTransferLines(models.Model):
    _name = 'inter.transfer.company.line'

class IntercompanyTransfer(models.Model):
    _name = 'inter.transfer.company'
