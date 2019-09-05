from odoo import api, fields, models


class AcquirerSequra(models.Model):
    _inherit = 'product.template'

    ends_in = fields.Char('Service end date', default='P6M', select=True, required=True, translate=False)
