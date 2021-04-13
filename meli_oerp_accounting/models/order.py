# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, osv, models, api
from odoo.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

import pdb
import requests

class SaleOrder(models.Model):

    _inherit = "sale.order"

    def action_invoice_create(self, grouped=False, final=False):

        _invoices = super(SaleOrder,self).action_invoice_create(grouped,final)

        #Colombia pragmatic
        for order in self:
            _logger.info(order)
            for inv in _invoices:
                _logger.info(inv)
                Invoice = self.env["account.invoice"].browse([inv])
                if Invoice.origin == order.name:
                    _logger.info(Invoice)
                    if "fecha_entrega" in Invoice._fields:
                        if not Invoice.fecha_entrega:
                            Invoice.fecha_entrega =  order.commitment_date or order.expected_date
                            _logger.info(Invoice.fecha_entrega)
        return _invoices


    def confirm_ml( self, meli=None, config=None ):
        _logger.info("meli_oerp_accounting confirm_ml")
        company = (config and 'company_id' in config._fields and config.company_id) or self.env.user.company_id
        config = config or company
        try:
            super(SaleOrder, self).confirm_ml(meli=meli,config=config)
            if (self.meli_orders):
                #process payments
                for meli_order in self.meli_orders:
                    for payment in meli_order.payments:
                        try:
                            if config.mercadolibre_process_payments_customer and not payment.account_payment_id:
                                payment.create_payment()
                        except Exception as e:
                            _logger.info("Error creating customer payment")
                            _logger.info(e, exc_info=True)
                        try:
                            if config.mercadolibre_process_payments_supplier_fea and not payment.account_supplier_payment_id:
                                payment.create_supplier_payment()
                        except Exception as e:
                            _logger.info("Error creating supplier fee payment")
                            _logger.info(e, exc_info=True)
                        try:
                            if config.mercadolibre_process_payments_supplier_shipment and not payment.account_supplier_payment_shipment_id and (payment.order_id and payment.order_id.shipping_list_cost>0.0):
                                payment.create_supplier_payment_shipment()
                        except Exception as e:
                            _logger.info("Error creating supplier shipment payment")
                            _logger.info(e, exc_info=True)
        except Exception as e:
            _logger.info("Confirm Payment Exception")
            _logger.error(e, exc_info=True)
            pass
        _logger.info("meli_oerp_accounting confirm_ml ended.")
