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

    def _meli_order_update( self, config=None ):

        for order in self:
            if ((order.meli_shipment and order.meli_shipment.logistic_type == "fulfillment")
                or order.meli_shipment_logistic_type=="fulfillment"):
                #seleccionar almacen para la orden
                order.warehouse_id = order._meli_get_warehouse_id(config=config)

    def _meli_get_warehouse_id( self, config=None ):

        company = (config and 'company_id' in config._fields and config.company_id) or self.env.user.company_id
        config = config or company
        wh_id = None

        if (config.mercadolibre_stock_warehouse):
            wh_id = config.mercadolibre_stock_warehouse

        if (self.meli_shipment_logistic_type == "fulfillment"):
            if (config.mercadolibre_stock_warehouse_full):
                wh_id = config.mercadolibre_stock_warehouse_full
        return wh_id

    #try to update order before confirmation (quotation)
    def confirm_ml( self, meli=None, config=None ):
        _logger.info("meli_oerp_stock confirm_ml")
        company = (config and 'company_id' in config._fields and config.company_id) or self.env.user.company_id
        config = config or company

        self._meli_order_update(config=config)

        super(SaleOrder, self).confirm_ml(meli=meli,config=config)

        #seleccionar en la confirmacion del stock.picking la informacion del carrier
        #
        _logger.info("meli_oerp_stock confirm_ml ended.")


class MercadolibreOrder(models.Model):

    _inherit = "mercadolibre.orders"

    #update order after any quotation/order confirmation
    def orders_update_order_json( self, data, context=None, config=None, meli=None ):

        super(MercadolibreOrder, self).orders_update_order_json( data=data, context=context, config=config, meli=meli)

        company = self.env.user.company_id

        if self.sale_order:
            self.sale_order._meli_order_update(config=config)
