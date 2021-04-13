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
#from .warning import warning
import requests

class OcapiConnectionBinding(models.Model):

    _name = "ocapi.connection.binding"
    _description = "Ocapi Connection Binding"
    #_inherit = "odoo_connector_api.connection.binding"

    #Connection reference defining mkt place credentials
    connection_account = fields.Many2one( "ocapi.connection.account", string="Odoo Connector Api Connection" )

    #Extern Connection Id binded to this object
    conn_id = fields.Char(string="Connector Id", index=True)

    #Connection Variation Id Binded to this object
    conn_variation_id = fields.Char(string="Connector Variation Id", index=True)

    #Connection Object Class Name to identify object
    class_id = fields.Char(string="Connector Class Id", index=True)

    active = fields.Boolean(string="Active",default=True,index=True)


class OcapiConnectionBindingProductTemplate(models.Model):

    _name = "ocapi.connection.binding.product_template"
    _description = "Ocapi Product Binding Product Template"
    _inherit = "ocapi.connection.binding"

    #Connection Product Templates Fields binding

    name = fields.Char(string="Name",index=True)
    sku = fields.Char(string="SKU",index=True)
    barcode = fields.Char(string="BARCODE",index=True)

    description = fields.Text(string="Description")

    price = fields.Float(string="Price",index=True)
    stock = fields.Float(string="Stock",index=True)

    full_update = fields.Datetime(string="Product update",index=True)
    image_update = fields.Datetime(string="Image update",index=True)
    price_update = fields.Datetime(string="Price update",index=True)
    stock_update = fields.Datetime(string="Stock update",index=True)

    stock_error = fields.Char(string="Stock Error", index=True )

    attributes = fields.Char(string="Attributes")

    product_tmpl_id = fields.Many2one("product.template",string="Product Template", help="Product Template")
    variant_bindings = fields.One2many("ocapi.connection.binding.product","binding_product_tmpl_id",string="Variant Bindings",help="Variant Bindings")

    image_bindings = fields.One2many('ocapi.product.image', "binding_product_tmpl_id", string="Product Template Images")

    _sql_constraints = [
        ('unique_conn_id_product_tmpl', 'unique(connection_account,conn_id,conn_variation_id,product_tmpl_id)', 'Binding exists for this item: product_tmpl_id!')
    ]

class OcapiConnectionBindingProductVariant(models.Model):

    _name = "ocapi.connection.binding.product"
    _description = "Ocapi Product Binding Product"
    _inherit = "ocapi.connection.binding.product_template"

    binding_product_tmpl_id = fields.Many2one("ocapi.connection.binding.product_template",string="Product Template Binding")
    product_id = fields.Many2one("product.product",string="Product Binding", help="Product Binding")

    image_bindings = fields.One2many('ocapi.product.image', "binding_product_variant_id", string="Product Variant Images")

    _sql_constraints = [
        ('unique_conn_id_variant', 'unique(connection_account,conn_id,conn_variation_id,product_id)', 'Binding exists for this item: product_id!')
    ]


class OcapiConnectionBindingSaleOrderPayment(models.Model):

    _name = "ocapi.binding.payment"
    _description = "Ocapi Sale Order Payment Binding"
    _inherit = "ocapi.connection.binding"

    name = fields.Char(string="Payment Name")
    account_payment_id = fields.Many2one("account.payment",string="Payment")

    _sql_constraints = [
        ('unique_conn_id_payment', 'unique(connection_account,conn_id,conn_variation_id,account_payment_id)', 'Binding exists for this item: payment!')
    ]

class OcapiConnectionBindingSaleOrderShipmentItem(models.Model):

    _name = "ocapi.binding.shipment.item"
    _description = "Ocapi Sale Order Shipment Item"
    _inherit = "ocapi.connection.binding"

    name = fields.Char(string="Shipment Product Item")
    shipping_id = fields.Many2one("ocapi.binding.shipment",string="Shipment")

    _sql_constraints = [
        ('unique_conn_id_shipment_item', 'unique(connection_account,conn_id,shipping_id)', 'Binding exists for this item: shipment.item!')
    ]

class OcapiConnectionBindingSaleOrderShipment(models.Model):

    _name = "ocapi.binding.shipment"
    _description = "Ocapi Sale Order Shipment Binding"
    _inherit = "ocapi.connection.binding"

    name = fields.Char(string="Shipment Name")

    order_id = fields.Many2one("ocapi.binding.sale_order",string="Order")
    products = fields.One2many("ocapi.binding.shipment.item", "shipping_id", string="Product Items")

    _sql_constraints = [
        ('unique_conn_id_shipment', 'unique(connection_account,conn_id,order_id)', 'Binding exists for this item: shipment!')
    ]

class OcapiConnectionBindingSaleOrderClient(models.Model):

    _name = "ocapi.binding.client"
    _description = "Ocapi Sale Order Client Binding"
    _inherit = "ocapi.connection.binding"

    name = fields.Char(string="Client Name")
    partner_id = fields.Many2one("res.partner",string="Partner")

    _sql_constraints = [
        ('unique_conn_id_res_partner', 'unique(connection_account,conn_id,conn_variation_id,partner_id)', 'Binding exists for this item: client!')
    ]

class OcapiConnectionBindingSaleOrderLine(models.Model):

    _name = "ocapi.binding.sale_order_line"
    _description = "Ocapi Sale Order Line Binding"
    _inherit = "ocapi.connection.binding"

    name = fields.Char(string="Order Line Name")

    #odoo order line
    sale_order_line = fields.Many2one("sale.order.line",string="Order Line")

    _sql_constraints = [
        ('unique_conn_id_sale_order_line', 'unique(connection_account,conn_id,conn_variation_id,sale_order_line)', 'Binding exists for this item: sale_order_line!')
    ]

class OcapiConnectionBindingSaleOrder(models.Model):

    _name = "ocapi.binding.sale_order"
    _description = "Ocapi Sale Order Binding"
    _inherit = "ocapi.connection.binding"

    name = fields.Char(string="Connector Order Name",index=True)
    status = fields.Selection( [
        #Initial state of an order, and it has no payment yet.
                                        ("confirmed","Confirmado"),
        #The order needs a payment to become confirmed and show users information.
                                      ("payment_required","Pago requerido"),
        #There is a payment related with the order, but it has not been accredited yet
                                    ("payment_in_process","Pago en proceso"),
        #The order has a related payment and it has been accredited.
                                    ("paid","Pagado"),
        #The order has not completed by some reason.
                                    ("cancelled","Cancelado")], string='Order Status');
    sale_order = fields.Many2one("sale.order",string="Sale Order")

    date_created = fields.Datetime(string="Date Created",index=True)
    date_closed = fields.Datetime(string='Closing Date',index=True)

    client = fields.Many2one("ocapi.binding.client",string="Client",index=True)
    lines = fields.Many2many("ocapi.binding.sale_order_line",string="Order Items")
    payments = fields.Many2many("ocapi.binding.payment",string="Order Payments")
    shipments = fields.Many2many("ocapi.binding.shipment",string="Order Shipments")

    _sql_constraints = [
        ('unique_conn_id_sale_order', 'unique(connection_account,conn_id,conn_variation_id,sale_order)', 'Binding exists for this item: sale_order!')
    ]

class OcapiConnectionBindingProductCategory(models.Model):

    _name = "ocapi.binding.category"
    _description = "Ocapi Product Binding Category"
    _inherit = "ocapi.connection.binding"

    name = fields.Char(string="Category",index=True)
    category_id = fields.Char(string="Category Id",index=True)

    _sql_constraints = [
        ('unique_conn_id_category', 'unique(connection_account,conn_id,conn_variation_id,category_id)', 'Binding exists for this item: category!')
    ]
