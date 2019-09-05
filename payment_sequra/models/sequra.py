# -*- coding: utf-'8' "-*-"

import logging
import requests
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class AcquirerSequra(models.Model):
    _inherit = 'payment.acquirer'

    sequra_user = fields.Char('Sequra User')
    sequra_pass = fields.Char('Sequra Password')
    sequra_merchant = fields.Char('Sequra Merchant')
    send_quotation = fields.Boolean('Send quotation', default=True)
    provider = fields.Selection(selection_add=[('sequra', 'SeQura')])
    return_ok_url = fields.Char('OK URL')

    def _get_sequra_api_urls(self):
        """ Sequra URLS """
        if self.environment == 'test':
            return 'https://sandbox.sequrapi.com'
        return 'https://live.sequrapi.com'

    @api.model
    def _get_sequra_urls(self, environment):
        return {'sequra_form_url': '/payment/sequra'}

    @api.multi
    def sequra_get_form_action_url(self):
        return self._get_sequra_urls(self.environment)['sequra_form_url']

    def request(self, endpoint, method='POST', data='{}', headers=None):
        if not headers:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        url = endpoint.find('http') == -1 and self._get_sequra_api_urls() + endpoint or endpoint
        if method == 'POST':
            return requests.post(
                url,
                auth=(self.sequra_user, self.sequra_pass),
                data=data,
                headers=headers
            )
        elif method == 'GET':
            return requests.get(
                url,
                auth=(self.sequra_user, self.sequra_pass),
                headers=headers
            )
        else:
            return requests.put(
                url,
                auth=(self.sequra_user, self.sequra_pass),
                data=data,
                headers=headers
            )


class TxSequra(models.Model):
    _inherit = 'payment.transaction'

    order_sequra_ref = fields.Char('Sequra order reference')
    provider = fields.Selection(related='acquirer_id.provider')

    sequra_conf_resp_status_code = fields.Char('Confirmation Response Status Code')
    sequra_conf_resp_reason = fields.Text('Confirmation Response Reason')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sequra_location = fields.Text('Sequra Location')
    order_sequra_ref = fields.Char('Sequra order reference', compute='_compute_sequra_ref')
    shipping_method = fields.Char('Sequra Shipping Method')

    @api.one
    @api.depends('sequra_location')
    def _compute_sequra_ref(self):
        s_location = self.sequra_location and self.sequra_location.split('/') or None
        self.order_sequra_ref = s_location and s_location[len(s_location) - 1] or ''

