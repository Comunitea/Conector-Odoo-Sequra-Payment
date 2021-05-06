# -*- coding: utf-8 -*-

from odoo import http
from odoo import release
from odoo.http import request
from odoo import SUPERUSER_ID, fields
from werkzeug.wrappers import BaseResponse as Response
from odoo import _
from datetime import datetime

import re
import os
import json
import pytz
import logging
_logger = logging.getLogger(__name__)


class SequraController(http.Controller):

    @http.route(['/sequra/shop/confirmation'], type='http', auth="public", website=True, csrf=False)
    def sequra_payment_confirmation(self, **post):
        # clean context and session, then redirect to the confirmation page
        request.website.with_context(request.context).sale_reset()
        return_ok_url = post.get('return_ok_url')
        if return_ok_url:
            return request.redirect(return_ok_url)
        return request.redirect('/shop/confirmation')

    @http.route('/checkout/sequra-ipn', type='http', auth='public', methods=['POST'], csrf=False, website=True)
    def checkout_sequra_ipn(self, **post):
        _logger.info("********Sequra IPN ***********")
        _logger.info("***************/checkout/sequra-ipn *******************")
        _logger.info(post)
        _logger.info("*******************************************************")

        order_ref = post.get('order_ref') # sequra reference
        order_ref_1 = post.get('order_ref_1') #odoo reference

        if order_ref and order_ref_1:
            order = request.env['sale.order'].sudo().search([('sequra_location', 'like', '%'+order_ref)], limit=1)
            if len(order):
                tx = request.env['payment.transaction'].sudo().search([('sale_order_ids', 'in', [order.id])],
                                                                      order='create_date desc', limit=1)
                if tx:
                    post = {
                        'merchant_id': tx.acquirer_id.sequra_merchant,
                        'return_ok_url': tx.acquirer_id.return_ok_url,
                    }
                    data = self._get_data_json(post, order, state='confirmed')
                    endpoint = order.sequra_location
                    response = tx.acquirer_id.request(endpoint, method='PUT', data=data)
                    values = {
                        'sequra_conf_resp_status_code': response.status_code,
                        'sequra_conf_resp_reason': response.reason
                    }
                    _logger.info("********************Response Code******************************")
                    _logger.info(response.status_code)
                    if 299 >= response.status_code >= 200:
                        values.update({
                            'state': 'done',
                            'order_sequra_ref': order_ref,
                        })
                        tx.sudo().write(values)
                        if tx.acquirer_id.send_quotation:
                            tx.sudo().sale_order_ids.force_quotation_send()
                            _logger.info("********************Quotation Send******************************")
                        print("tx.sudo().sale_order_ids: {}".format(tx.sudo().sale_order_ids))
                        result = tx.sudo().sale_order_ids.action_confirm()
                        print("action result: {}".format(result))
                        _logger.info("********************Quotation Confirmed******************************")
                        invoices = tx.sudo().sale_order_ids.action_invoice_create()
                        _logger.info("********************Invoice Created******************************")
                        tx.account_invoice_id = request.env['account.invoice'].browse(invoices and invoices[0] or [])
                        if tx.account_invoice_id:
                            tx.account_invoice_id.sudo().action_invoice_open()
                            _logger.info("********************Invoice Open******************************")
                            tx._confirm_invoice()
                            _logger.info("********************Invoice Pay******************************")
                        return Response('OK', status=200)
                    elif response.status_code == 409:
                        _logger.info("***************/checkout/sequra-ipn *******************")
                        _logger.info("Cart has changed")
                        return Response('Conflict', status=409)
                    else:
                        _logger.info("***************/checkout/sequra-ipn *******************")
                        _logger.info("Error found in sequra response with status code %s" % response.status_code)
                        return Response(response.reason, status=response.status_code)
            else:
                _logger.info("***************/checkout/sequra-ipn *******************")
                _logger.info("order_ref_1 = %s no found in odoo" % order_ref_1)
                return Response('Not Found', status=404)

        else:
            _logger.info("***************/checkout/sequra-ipn *******************")
            _logger.info("********One or either order reference empty ***********")
            _logger.info("order_ref = %s" % order_ref)
            _logger.info("order_ref_1 = %s" % order_ref_1)

    @http.route('/payment/sequra', type='http', auth='public', methods=['POST'], csrf=False, website=True)
    def payment_sequra(self, **post):
        print("payment_sequra")
        acquirer_obj = request.env['payment.acquirer'].sudo(SUPERUSER_ID).browse(int(post.get('acquirer_id', -1)))
        print("acquirer_obj: {}".format(acquirer_obj))
        order = request.website.sale_get_order()
        print("order: {}".format(order))
        r = self.start_solicitation(acquirer_obj, post, order)
        print("r: {}".format(r))
        print("r.status_code: {}".format(r.status_code))
        if r.status_code == 204:
            location = r.headers.get('Location')
            method_payment = post.get('payment_method')
            r = self.fetch_id_form(acquirer_obj, location, method_payment)
            if r.status_code == 200:
                order.write({
                    'sequra_location': location
                })
                values = {
                    'partner': order.partner_id.id,
                    'order': order,
                    'errors': [],
                    'iframe': r.content
                }
                self.render_payment_acquirer(order, values)
                return request.render("payment_sequra.payment", values)
        json = r.json()
        error = json and len(json['errors']) and json['errors'][0] or ''
        return request.render("payment_sequra.500", {'error': error})

    def start_solicitation(self, acquirer_id,  post, order):
        post.update({
            'merchant_id': acquirer_id.sequra_merchant,
            'return_ok_url': acquirer_id.return_ok_url,
        })
        data = self._get_data_json(post, aorder=order)
        endpoint = '/orders'
        r = acquirer_id.request(endpoint, data=data)
        return r

    def fetch_id_form(self, acquirer_id, location, payment_method=None):
        headers = {
            'Accept': 'text/html'
        }
        endpoint = '%s/form_v2' % location
        if payment_method:
            endpoint += '?product=%s' % payment_method
        r = acquirer_id.request(endpoint, 'GET', headers=headers)
        return r

    def _get_customer_data(self, partner_id, order_id):
        order_ids = request.env['sale.order'].sudo().search([('partner_id', '=', partner_id.id),
                                                      ('id', '!=', order_id)], limit=10, order='create_date desc')

        previous_orders = [{
            'created_at': fields.Datetime.from_string(o.create_date).
                          replace(tzinfo=pytz.timezone(o.partner_id.tz or 'Europe/Madrid'), microsecond=0).isoformat(),
            'amount': int(round(o.amount_total * 100, 2)),
            'currency': o.currency_id.name} for o in order_ids]
        customer = self._get_address(partner_id)
        if "HTTP_X_FORWARDED_FOR" in request.httprequest.environ:
        # Virtual host        
            ip = request.httprequest.environ["HTTP_X_FORWARDED_FOR"]
        elif "HTTP_HOST" in request.httprequest.environ:
            # Non-virtualhost
            ip = request.httprequest.environ["REMOTE_ADDR"]
        customer['email'] = partner_id.email or ""
        customer['language_code'] = "es-ES"
        customer['ref'] = partner_id.id
        customer['company'] = partner_id.parent_id.name or ""
        customer['logged_in'] = 'unknown'
        customer['ip_number'] = ip
        customer['user_agent'] = request.httprequest.environ["HTTP_USER_AGENT"]
        customer['vat_number'] = partner_id.vat or ""
        customer['previous_orders'] = previous_orders
        return customer

    def _get_address(self, partner_id):
        def _partner_split_name(partner_name):
            return [' '.join(partner_name.split()[:1]), ' '.join(partner_name.split()[1:])]

        return {
            "given_names": _partner_split_name(partner_id.name)[0],
            "surnames": _partner_split_name(partner_id.name)[1],
            "company": partner_id.parent_id.name or "",
            "address_line_1": partner_id.street or "",
            "address_line_2": partner_id.street2 or "",
            "postal_code": partner_id.zip or "",
            "city": partner_id.city or "",
            "country_code": partner_id.country_id.code or "",
            "phone": partner_id.phone or "",
            "mobile_phone": partner_id.mobile or "",
            "nin": partner_id.vat or ""
        }

    def _get_items(self, order_id, shipping_name):
        items = []
        for sol in order_id.order_line:
            price_subtotal = sol.price_subtotal
            total_without_tax = int(round(price_subtotal * 100, 2))
            price_without_tax = int(round((price_subtotal / sol.product_uom_qty) * 100, 2))

            tax = sol.price_tax if price_subtotal else 0
            tax = round(tax, 2)

            total_with_tax = int(round((price_subtotal + tax) * 100, 2))
            print("price_subtotal + tax : {} + {} = {}".format(price_subtotal, tax, total_with_tax))
            price_with_tax = int(round(((price_subtotal + tax)/sol.product_uom_qty) * 100, 2))

            if order_id.carrier_id.name != sol.name:
                item = {
                    "reference": str(sol.product_id.id),
                    "name": sol.name,
                    "quantity": int(sol.product_uom_qty),
                    "price_with_tax": price_with_tax,
                    "total_with_tax": total_with_tax,
                    "downloadable": False,#@todo
                    "product_id": sol.product_id.id,
                }
                if sol.product_id.type=='service':
                    item['type'] = 'service'
                    item['ends_in'] = sol.product_id.ends_in
            else:
                item = {
                    "type": "handling",
                    "reference": "Costes de envío",
                    "name": shipping_name,
                    "tax_rate": 0,
                    "total_with_tax": total_with_tax,
                    "total_without_tax": total_without_tax,
                }

            items.append(item)

        return items

    def _get_data_json(self, post, aorder=None, state=''):
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

        notify_url = '%s/checkout/sequra-ipn' % base_url

        order = aorder

        return_ok_url = post.get('return_ok_url')

        return_url = '%s/sequra/shop/confirmation?payment_method=sq-SQ_PRODUCT_CODE&return_ok_url=%s' % (
                     base_url, return_ok_url)  # '%s/checkout/sequra-confirmed' % base_url

        partner_id = order.partner_id
        partner_invoice_id = order.partner_invoice_id
        partner_shipping_id = order.partner_shipping_id

        company_id = request.env['ir.model.data'].sudo(SUPERUSER_ID).xmlid_to_res_id('base.main_company')
        company_id = request.env['res.company'].sudo(SUPERUSER_ID).browse(company_id)
        currency = company_id.currency_id.name

        merchant_id = post.get('merchant_id')

        merchant_values = {
            "id": merchant_id,
            "notify_url": notify_url,
            "return_url": return_url,
            "notification_parameters": {
                "test": 'test'
            }
        }
        carrier_name = "no shipping"
        if order.carrier_id:
            carrier_name = order.carrier_id.name

        print("order.amount_total: {}".format(order.amount_total))

        json_items = json.dumps(
            {
                "order": {
                    "state": state,
                    "merchant": merchant_values,
                    "merchant_reference": {
                        "order_ref_1": order.name
                    },
                    "cart": {
                        "cart_ref": order.name,
                        "currency": currency or "EUR",
                        "gift": False,
                        "items": self._get_items(order, ''),#@todo second argument should be shipping method
                        "order_total_with_tax": int(round((order.amount_total) * 100, 2))
                    },
                    "delivery_address": self._get_address(partner_shipping_id),
                    "invoice_address": self._get_address(partner_invoice_id),
                    "customer": self._get_customer_data(partner_id, order.id),
                    "delivery_method": {
                        "name": carrier_name,#@todo
                    },
                    "gui": {
                        "layout": "desktop"#@todo
                    },
                    "platform": {
                        "name": "Odoo",
                        "version": release.version,
                        "uname": " ".join(os.uname()),
                        "db_name": "postgresql",
                        "db_version": "9.4"#@todo
                    }
                }
            }
        )

        print("json_items: {}".format(json_items))

        return json_items

    def render_payment_acquirer(self, order, values):
        shipping_partner_id = False
        if order:
            if order.partner_shipping_id.id:
                shipping_partner_id = order.partner_shipping_id.id
            else:
                shipping_partner_id = order.partner_invoice_id.id

        acquirer_ids = request.env['payment.acquirer'].sudo(SUPERUSER_ID).search(
                                          [('website_published', '=', True), ('company_id', '=', order.company_id.id)])
        values['acquirers'] = acquirer_ids
        render_ctx = dict(request.env.context, submit_class='btn btn-primary', submit_txt=_('Pay Now'))
        for acquirer in values['acquirers']:
            acquirer.button = acquirer.with_context(render_ctx).sudo(SUPERUSER_ID).render(
                                order.name,
                                order.amount_total,
                                order.pricelist_id.currency_id.id,
                                partner_id=shipping_partner_id,
                                values={'return_url': '/shop/payment/validate'})


    @http.route(['/sequra/is_enabled'], type='http', auth="public", methods=['GET'], website=True)
    def get_sequra_is_enabled_json(self):
        domain = ['&', ('website_published', '=', True), ('provider', 'ilike', 'SeQura')]
        acquirers = request.env['payment.acquirer'].search(domain)
        return json.dumps({
            'sequra': len(acquirers) > 0
        })
