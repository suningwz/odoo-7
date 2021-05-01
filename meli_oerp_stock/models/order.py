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
import re

from .product_sku_rule import *

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

    #mapping procedure params: sku or item
    def map_meli_sku( self, meli_sku=None, meli_item=None ):
        _logger.info("map_meli_sku: "+str(meli_item))
        odoo_sku = None
        mapped = None
        filtered = None
        seller_sku = meli_sku or (meli_item and 'seller_sku' in meli_item and meli_item['seller_sku']) or (meli_item and 'seller_custom_field' in meli_item and meli_item['seller_custom_field'])

        if seller_sku:
            #mapped skus (json dict string assigned)
            if mapping_meli_sku_regex:
                for reg in mapping_meli_sku_regex:
                    rules = mapping_meli_sku_regex[reg]
                    for rule in rules:
                        regex = "regex" in rule and rule["regex"]
                        if regex and not filtered:
                            group = "group" in rule and rule["group"]
                            c = re.compile(regex)
                            if c:
                                ms = c.findall(seller_sku)
                                if ms:
                                    if len(ms)>group:
                                        m = ms[group]
                                        filtered = m
                                        _logger.info("filtered ok: regex: "+str(rule)+" result: "+str(m))
                                        break;

            mapped_sku = (mapping_meli_sku_defaut_code and seller_sku in mapping_meli_sku_defaut_code and mapping_meli_sku_defaut_code[seller_sku])
            odoo_sku = mapped_sku or filtered or seller_sku

        if mapped_sku:
            _logger.info("map_meli_sku(): meli_sku: "+str(seller_sku)+" mapped to: "+str(odoo_sku))

        return odoo_sku

    #extended from mercadolibre.orders: SKU formulas
    def _search_meli_product( self, meli=None, meli_item=None, config=None ):
        _logger.info("search_meli_product extended: "+str(meli_item))
        product_related = super(MercadolibreOrder, self).search_meli_product( meli=meli, meli_item=meli_item, config=config )

        product_obj = self.env['product.product']
        if ( len(product_related)==0 and ('seller_custom_field' in meli_item or 'seller_sku' in meli_item)):

            #Mapping meli sku to odoo sku
            meli_item["seller_sku"] = self.map_meli_sku( meli_item=meli_item )

            #1ST attempt "seller_sku" or "seller_custom_field"
            seller_sku = ('seller_sku' in meli_item and meli_item['seller_sku']) or ('seller_custom_field' in meli_item and meli_item['seller_custom_field'])
            if (seller_sku):
                product_related = product_obj.search([('default_code','=',seller_sku)])

            #2ND attempt only old "seller_custom_field"
            if (not product_related and 'seller_custom_field' in meli_item):
                seller_sku = ('seller_custom_field' in meli_item and meli_item['seller_custom_field'])
            if (seller_sku):
                product_related = product_obj.search([('default_code','=',seller_sku)])

        #product_obj = self.env['product.product']

        return product_related
