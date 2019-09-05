# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import json
import logging
from odoo.exceptions import ValidationError
from odoo import release
import os

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def action_done(self):
        result = super(StockPicking, self).action_done()
        for picking in self:
            if picking.sale_id:
                tx = self.env['payment.transaction'].search([('sale_order_id', '=', picking.sale_id.id),
                                                             ('acquirer_id.provider', '=', 'sequra')], limit=1)
                _logger.info("********************TX******************************")
                _logger.info(tx)
                if tx:
                    endpoint = '/merchants/%s/orders/%s' % (tx.acquirer_id.sequra_merchant, tx.reference)
                    _logger.info("********************Endpoint******************************")
                    _logger.info(endpoint)
                    data = self._get_data_json(tx.acquirer_id.sequra_merchant, tx.reference)
                    _logger.info("********************Data******************************")
                    _logger.info(data)
                    response = tx.acquirer_id.request(endpoint, method='PUT', data=data)
                    _logger.info("********************Response******************************")
                    _logger.info(response.reason)
                    _logger.info(response.history)
                    _logger.info(response._content)
                    _logger.info(response._content_consumed)
                    _logger.info(response.text)
        return result

    @api.model
    def _get_items(self):
        items = []
        unshipped_items = []
        order_total_with_tax = 0
        unshipped_total_with_tax = 0
        s_line = []
        for move in self.move_lines:
            if move.sale_line_id:
                price_subtotal = move.sale_line_id.price_subtotal
                tax = move.sale_line_id.price_tax if price_subtotal else 0
                price_with_tax = int(round(((price_subtotal + tax) / move.sale_line_id.product_uom_qty) * 100, 2))
                total_with_tax = int(price_with_tax * move.product_uom_qty)
                item = {
                    "reference": str(move.sale_line_id.product_id.id),
                    "name": move.sale_line_id.name,
                    "quantity": int(move.product_uom_qty),
                    "price_with_tax": price_with_tax,
                    "total_with_tax": total_with_tax,
                    "downloadable": False,
                    "product_id": move.product_id.id,
                }
                items.append(item)
                order_total_with_tax += total_with_tax
                s_line.append(move.sale_line_id.id)
                if move.product_uom_qty < move.sale_line_id.product_uom_qty:
                    rest_qty = move.sale_line_id.product_uom_qty - (move.product_uom_qty + move.sale_line_id.qty_delivered)
                    price_with_tax_un = int(round(((price_subtotal + tax) / rest_qty) * 100, 2))
                    total_with_tax_un = int(price_with_tax_un * rest_qty)
                    item.update({"quantity": int(rest_qty),
                                 "price_with_tax": price_with_tax_un,
                                 "total_with_tax": total_with_tax_un})
                    unshipped_items.append(item)
                    unshipped_total_with_tax += total_with_tax_un
        for line in self.sale_id.order_line:
            if line.id not in s_line and line.product_id.type != 'service':
                price_subtotal = line.price_subtotal
                tax = line.price_tax if price_subtotal else 0
                price_with_tax_un = int(round(((price_subtotal + tax) / line.product_uom_qty) * 100, 2))
                total_with_tax_un = int(price_with_tax_un * line.product_uom_qty)
                item = {
                    "reference": str(line.product_id.id),
                    "name": line.name,
                    "quantity": int(line.product_uom_qty),
                    "price_with_tax": price_with_tax_un,
                    "total_with_tax": total_with_tax_un,
                    "downloadable": False,
                    "product_id": line.product_id.id,
                }
                unshipped_items.append(item)
                unshipped_total_with_tax += total_with_tax_un
        return order_total_with_tax, items, unshipped_total_with_tax, unshipped_items

    @api.model
    def _get_data_json(self, merchant_id, order_name):
        order_total_with_tax, items, unshipped_total_with_tax,  unshipped_items= self._get_items()
        data = {
                "order": {
                    "state": '',
                    "merchant": {
                        "id": merchant_id,
                    },
                    "merchant_reference": {
                        "order_ref_1": order_name
                    },
                    "unshipped_cart": {
                        "currency": "EUR",
                        "order_total_with_tax": 0,
                        "items": []
                    },
                    "shipped_cart": {
                        "currency": "EUR",
                        "order_total_with_tax": order_total_with_tax,
                        "items": items
                    },
                    "platform": {
                        "name": "Odoo",
                        "version": release.version,
                        "uname": " ".join(os.uname()),
                        "db_name": "postgresql",
                        "db_version": "9.4"
                    }
                }
            }
        return json.dumps(data)
