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

from . import versions
from .versions import *

from odoo.exceptions import UserError, ValidationError


class MercadoLibreConnectionBinding(models.Model):

    _name = "mercadolibre.binding"
    _description = "MercadoLibre Connection Binding"
    _inherit = "ocapi.connection.binding"

    #Connection reference defining mkt place credentials
    connection_account = fields.Many2one( "mercadolibre.account", string="MercadoLibre Account" )

class MercadoLibreConnectionBindingProductTemplate(models.Model):

    _name = "mercadolibre.product_template"
    _description = "MercadoLibre Product Binding Product Template"
    _inherit = "ocapi.connection.binding.product_template"

    connection_account = fields.Many2one( "mercadolibre.account", string="MercadoLibre Account" )
    variant_bindings = fields.One2many("mercadolibre.product","binding_product_tmpl_id",string="Product Variant Bindings")

    image_bindings = fields.One2many('mercadolibre.product.image', "binding_product_tmpl_id", string="Product Template Images")


    meli_title = fields.Char(string='Nombre del producto en Mercado Libre',size=256)
    meli_description = fields.Text(string='Descripción')
    meli_category = fields.Many2one("mercadolibre.category","Categoría de MercadoLibre")
    meli_buying_mode = fields.Selection( [("buy_it_now","Compre ahora"),("classified","Clasificado")], string='Método de compra')
    meli_price = fields.Char(string='Precio de venta', size=128)
    meli_currency = fields.Selection([("ARS","Peso Argentino (ARS)"),
                                    ("MXN","Peso Mexicano (MXN)"),
                                    ("COP","Peso Colombiano (COP)"),
                                    ("PEN","Sol Peruano (PEN)"),
                                    ("BOB","Boliviano (BOB)"),
                                    ("BRL","Real (BRL)"),
                                    ("CLP","Peso Chileno (CLP)"),
                                    ("CRC","Colon Costarricense (CRC)"),
                                    ("UYU","Peso Uruguayo (UYU)"),
                                    ("USD","Dolar Estadounidense (USD)")],
                                    string='Moneda')
    meli_condition = fields.Selection([ ("new", "Nuevo"),
                                        ("used", "Usado"),
                                        ("not_specified","No especificado")],
                                        'Condición del producto')
    meli_dimensions = fields.Char( string="Dimensiones del producto", size=128)
    meli_pub = fields.Boolean('Meli Publication',help='MELI Product',index=True)
    meli_master = fields.Boolean('Meli Producto Maestro',help='MELI Product Maestro',index=True)
    meli_warranty = fields.Char(string='Garantía', size=256)
    meli_listing_type = fields.Selection([("free","Libre"),("bronze","Bronce"),("silver","Plata"),("gold","Oro"),("gold_premium","Gold Premium"),("gold_special","Gold Special/Clásica"),("gold_pro","Oro Pro")], string='Tipo de lista')
    meli_attributes = fields.Text(string='Atributos')

    #meli_publications = fields.Text(compute=product_template_stats,string='Publicaciones en ML',search=search_template_stats)
    #meli_variants_status = fields.Text(compute=product_template_stats,string='Meli Variant Status')

    meli_pub_as_variant = fields.Boolean('Publicar variantes como variantes en ML',help='Publicar variantes como variantes de la misma publicación, no como publicaciones independientes.')
    meli_pub_variant_attributes = fields.Many2many(prod_att_line, relation='meli_pub_variant_attributes',column1='mercadolibre_product_template_id',column2='product_template_attribute_line_id', string='Atributos a publicar en ML',help='Seleccionar los atributos a publicar')
    meli_pub_principal_variant = fields.Many2one( 'product.product',string='Variante principal',help='Variante principal')

    meli_model = fields.Char(string="Modelo [meli]",size=256)
    meli_brand = fields.Char(string="Marca [meli]",size=256)
    meli_stock = fields.Float(string="Cantidad inicial (Solo para actualizar stock)[meli]")

    meli_product_bom = fields.Char(string="Lista de materiales (skux:1,skuy:2,skuz:4) [meli]")

    meli_product_price = fields.Float(string="Precio [meli]")
    meli_product_cost = fields.Float(string="Costo del proveedor [meli]")
    meli_product_code = fields.Char(string="Codigo de proveedor [meli]")
    meli_product_supplier = fields.Char(string="Proveedor del producto [meli]")

    meli_ids = fields.Char(size=2048,string="MercadoLibre Ids.",help="ML Ids de variantes separados por coma.",index=True)

    meli_catalog_listing = fields.Boolean(string='Catalog Listing', size=256)
    meli_catalog_product_id = fields.Char(string='Catalog Product Id', size=256)
    meli_catalog_item_relations = fields.Char(string='Catalog Item Relations', size=256)
    meli_catalog_automatic_relist = fields.Boolean(string='Catalog Auto Relist', size=256)

    meli_shipping_logistic_type = fields.Char(string="Logistic Type",index=True)

    def product_template_post( self, context=None, meli_id=None, meli=None, account=None, product_variant=None ):
        context = context or self.env.context
        _logger.info("MercadoLibre Product template Post context: "+str(context)+" meli_id: "+str(meli_id)+" account: "+str(account))
        warningobj = self.env['warning']
        custom_context = {}
        force_meli_pub = False
        force_meli_active = False
        force_meli_new_pub = False

        if ("force_meli_pub" in context):
            force_meli_pub = context.get("force_meli_pub")
        if ("force_meli_active" in context):
            force_meli_active = context.get("force_meli_active")
        if ("force_meli_new_pub" in context):
            force_meli_new_pub = context.get("force_meli_new_pub")

        custom_context = { "force_meli_pub": force_meli_pub, "force_meli_active": force_meli_active, "force_meli_new_pub": force_meli_new_pub }
        _logger.info("custom_context: "+str(custom_context))

        ret = {}
        posted_products = 0

        for bindT in self:

            account = bindT.connection_account
            company = (account and account.company_id) or self.env.user.company_id
            config = (account and account.configuration) or company
            productT = bindT.product_tmpl_id
            meli_id = bindT.conn_id

            if not meli:
                meli = self.env['meli.util'].get_new_instance( account.company_id, account )

            if (productT.meli_pub_as_variant):
                _logger.info("Posting as variants")

                if productT.meli_pub_principal_variant and productT.meli_pub_principal_variant.meli_id == meli_id:
                    variant = productT.meli_pub_principal_variant
                    variant.meli_pub = True
                    ret = variant.with_context(custom_context).product_post( meli=meli, config=config )
                    if ('name' in ret[0]):
                        return ret[0]
                    posted_products+= 1
                    bindT.stock = 0
                    for variant in productT.product_variant_ids:
                        if variant.meli_id:
                            #binding is anew, set with last meli_id if we can
                            meli_id = variant.meli_id
                            meli_price = variant.meli_price
                            meli_available_quantity = variant.meli_available_quantity

                            bindT.conn_id = meli_id
                            bindT.price = meli_price
                            bindT.stock+= float(meli_available_quantity)

                            for bind in bindT.variant_bindings:
                                bind.conn_id = meli_id
                                bind.price = meli_price
                    #continue;
                else:
                    #binded but not principal variants.meli_id != bindT.meli_id
                    _logger.info("TODO: Check this bind how to post it!!!")
                    return ret

                #filtrar las variantes que tengan esos atributos que definimos
                #la primera variante que cumple las condiciones es la que publicamos.
                variant_principal = False
                #las condiciones es que los atributos de la variante
                conditions_ok = True
                for variant in productT.product_variant_ids:
                    if (variant._conditions_ok() ):
                        variant.meli_pub = True
                        if (variant_principal==False):
                            _logger.info("Posting variant principal:")
                            _logger.info(variant)
                            variant_principal = variant
                            productT.meli_pub_principal_variant = variant
                            ret = variant.with_context(custom_context).product_post( meli=meli, config=config )
                            if ('name' in ret[0]):
                                return ret[0]
                            posted_products+= 1

                        else:
                            if (variant_principal):
                                ret = variant.with_context(custom_context).product_post_variant(variant_principal)
                                #if ('name' in ret[0]):
                                #    return ret[0]
                                #posted_products+= 1
                    else:
                        _logger.info("No condition met for:"+variant.display_name)
                _logger.info(productT.meli_pub_variant_attributes)
            else:
                for variant in productT.product_variant_ids:
                    _logger.info("product_template_post > Posting Variant: ", variant, variant.meli_pub)
                    if product_variant and product_variant.id!=variant.id:
                        #only one product variant to import on this iteration
                        continue;

                    if (force_meli_pub==True):
                        variant.meli_pub = True

                    if force_meli_new_pub:
                        meli_id = False

                    first_product_post = (not meli_id and not variant.meli_id)
                    new_product_post = (variant.meli_id and not meli_id) and force_meli_new_pub
                    update_product_post = (variant.meli_id and not meli_id) and force_meli_new_pub

                    _logger.info("meli_id:"+str(meli_id)+" variant.meli_id:"+str(variant.meli_id)+" force_meli_new_pub:"+str(force_meli_new_pub))
                    _logger.info("first_product_post:"+str(first_product_post)+" new_product_post:"+str(new_product_post)+" update_product_post:"+str(update_product_post))

                    if (variant.meli_pub and (variant.meli_id==meli_id or first_product_post) ):

                        _logger.info("Posting variant")
                        ret = variant.with_context(custom_context).product_post( meli=meli, config=config )
                        if ('name' in ret[0]):
                            return ret[0]
                        _logger.info(ret)

                        if variant.meli_id:
                            #binding is anew, set with last meli_id if we can
                            meli_id = variant.meli_id
                            meli_price = variant.meli_price
                            meli_available_quantity = variant.meli_available_quantity
                            bindT.conn_id = meli_id
                            bindT.price = meli_price
                            bindT.stock = meli_available_quantity
                            for bind in bindT.variant_bindings:
                                bind.conn_id = meli_id
                                bind.price = meli_price
                                #bind.stock = meli_available_quantity

                        posted_products+= 1
                    elif (new_product_post and force_meli_new_pub):
                        _logger.info("Posting New variant Publication")
                        bind = bindT and bindT.variant_bindings and bindT.variant_bindings[0]
                        ret = variant.with_context(custom_context).product_post( bind_tpl=bindT, bind=bind, meli=meli, config=config )
                        if ('name' in ret[0]):
                            #return ret[0]
                            _logger.info(ret)
                            raise ValidationError(str(ret[0]))
                        if bind.meli_id:
                            #binding is anew, set with last meli_id if we can
                            meli_id = bind.meli_id
                            meli_price = bind.meli_price
                            meli_available_quantity = bind.meli_available_quantity
                            bindT.conn_id = meli_id
                            bindT.price = meli_price
                            bindT.stock = meli_available_quantity
                            for bind in bindT.variant_bindings:
                                bind.conn_id = meli_id
                                bind.meli_id = meli_id
                                bind.price = meli_price
                                #bind.stock = meli_available_quantity
                        _logger.info(ret)
                        posted_products+= 1
                    else:
                        #if error_product_post:
                        #    _logger.info("error_product_post: "+str(error_product_post))
                        #binding is new, take the first variant meli_id:
                        error = "No meli_pub or meli_id for:"+variant.display_name + " bind>meli_id: "+str(meli_id) + " meli_pub:" + str(variant.meli_pub) + " variant.meli_id:"+str(variant.meli_id)
                        #+ " error_product_post:"+str(error_product_post)
                        raise ValidationError(error)
                        _logger.info(error)

        if (posted_products==0):
            raise ValidationError("Se intentaron publicar 0 productos. Debe forzar las publicaciones o marcar el producto con el campo Meli Publication, debajo del titulo. Puede tambien intentar revincular el producto.")
            ret = warningobj.info( title='MELI WARNING', message="Se intentaron publicar 0 productos. Debe forzar las publicaciones o marcar el producto con el campo Meli Publication, debajo del titulo. Puede tambien intentar revincular el producto.", message_html="" )

        return ret

    def product_template_post_stock( self, context=None, meli_id=None, meli=None, account=None ):
        _logger.info("template product_template_update >> MercadoLibre Product template Update")
        ret = {}
        for bindT in self:

            account = bindT.connection_account
            product = bindT.product_tmpl_id
            meli_id = bindT.conn_id

            if not meli:
                meli = self.env['meli.util'].get_new_instance( account.company_id, account )

            for bindv in bindT.variant_bindings:
                bindv.product_post_stock(meli=meli)

        return ret

    def product_template_update( self, meli=None ):
        _logger.info("template product_template_update >> MercadoLibre Product template Update")
        ret = {}
        for bindT in self:

            account = bindT.connection_account
            product = bindT.product_tmpl_id
            meli_id = bindT.conn_id

            if not meli:
                meli = self.env['meli.util'].get_new_instance( account.company_id, account )

            rjson = account.fetch_meli_product( meli_id = meli_id, meli = meli )

            if ( product and product.meli_pub_as_variant and product.meli_pub_principal_variant.id ):
                _logger.info("template product_template_update >> Updating principal variant")
                #como puede que no exista aun el binding de variant??? que hacemos??
                #chequear si tiene un binding de variante:  y ejecutar ese binding
                pvbind = self.env["mercadolibre.product"].search([  ('conn_id','=',meli_id),
                                                                    ('product_tmpl_id','=',product.id),
                                                                    ('product_id','=',product.meli_pub_principal_variant.id),
                                                                    ('connection_account','=',account.id)],limit=1)
                if pvbind:
                    pvbind.product_meli_get_product( meli=meli )
                else:
                    ret = product.meli_pub_principal_variant.product_meli_get_product( account=account, meli=meli, rjson=rjson )
                    _logger.info("ret:"+str(ret))
                    _logger.info("MercadoLibre Product template Update >> Updating principal variant >> copy_from_rjson (recursive)")
                    bindT.copy_from_rjson( rjson=rjson, meli=meli )
            else:
                for variant in product.product_variant_ids:
                    #_logger.info("Variant:", variant)
                    if (variant.meli_pub):
                        _logger.info("template product_template_update >> calling product_meli_get_product Updating variant")
                        pvbind = self.env["mercadolibre.product"].search([  ('conn_id','=',meli_id),
                                                                            ('product_tmpl_id','=',product.id),
                                                                            ('product_id','=',variant.id),
                                                                            ('connection_account','=',account.id)],limit=1)
                        ret = {}
                        if pvbind:
                            pvbind.product_meli_get_product( meli=meli, rjson=rjson )
                        else:
                            ret = variant.product_meli_get_product(account=account, meli=meli, rjson=rjson)
                        if ('name' in ret):
                            return ret

        return ret

        #if (product_template):
        #    bindT = product_template.mercadolibre_bind_to( account=account, meli_id=meli_id, bind_variants=True )
        #    if bindT:
                # from_meli_oerp = True copy form recent imported
        #        bindT.fetch_meli_product( meli=meli, from_meli_oerp=True, fetch_variants=True )

    def category_predictor( self ):
        _logger.info("MercadoLibre Product template Category Predictor")

    def copy_from_meli_oerp( self ):
        for bindT in self:
            productT = bindT.product_tmpl_id
            #basic info
            bindT.meli_title = productT.meli_title
            bindT.meli_description = productT.meli_description
            bindT.meli_category = productT.meli_category
            bindT.meli_price = productT.meli_price
            bindT.price = productT.meli_price
            bindT.meli_stock = productT.meli_stock
            bindT.stock = productT.meli_stock

            #attributes
            bindT.meli_attributes = productT.meli_attributes
            bindT.meli_model = productT.meli_model
            bindT.meli_brand = productT.meli_brand

            #publish ref info
            bindT.meli_pub = productT.meli_pub
            bindT.meli_master = productT.meli_master
            bindT.meli_ids = productT.meli_ids

            #config info
            bindT.meli_currency = productT.meli_currency
            bindT.meli_condition = productT.meli_condition
            bindT.meli_warranty = productT.meli_warranty
            bindT.meli_listing_type = productT.meli_listing_type
            bindT.meli_dimensions = productT.meli_dimensions
            bindT.sku = productT.product_variant_ids.mapped("default_code") or productT.default_code
            bindT.barcode = productT.product_variant_ids.mapped("barcode") or productT.barcode

            bindT.meli_shipping_logistic_type = str(productT.product_variant_ids.mapped("meli_shipping_logistic_type"))


    def copy_from_rjson( self, rjson, meli=None ):
        _logger.info("template bind >> copy_from_rjson")
        if not rjson:
            return
        for bindT in self:
            account = bindT.connection_account
            config = account.configuration
            product_tmpl_id = bindT.product_tmpl_id
            #basic info
            catid, wwwid = self.env["mercadolibre.category"].meli_get_category( rjson['category_id'], meli=meli, create_missing_website=config.mercadolibre_create_website_categories )
            desplain = ("description" in rjson and rjson["description"]) or ""
            meli_ids = rjson["id"]
            seller_sku = product_tmpl_id.product_variant_ids.mapped("default_code") or ("seller_sku" in rjson and rjson["seller_sku"]) or product_tmpl_id.default_code
            barcode = product_tmpl_id.product_variant_ids.mapped("barcode") or ("barcode" in rjson and rjson["barcode"]) or product_tmpl_id.barcode
            fields = {
                #'meli_permalink': rjson['permalink'],
                'meli_title': rjson['title'].encode("utf-8"),
                'meli_description': desplain,
                'meli_listing_type': rjson['listing_type_id'],
                'meli_buying_mode':rjson['buying_mode'],
                'meli_price': str(rjson['price']),
                'price': str(rjson['price']),
                'meli_currency': rjson['currency_id'],
                'meli_condition': rjson['condition'],
                #'meli_available_quantity': rjson['available_quantity'],
                'meli_warranty': rjson['warranty'],
                'meli_category': catid,
                'meli_ids': meli_ids,
                'sku': seller_sku or "",
                'barcode': barcode or ""
                #'meli_imagen_link': rjson['thumbnail'],
                #'meli_video': str(vid),
                #'meli_dimensions': meli_dim_str,
            }
            meli_shipping_logistic_type = ( rjson and "shipping" in rjson and "logistic_type" in rjson["shipping"] and rjson["shipping"]["logistic_type"] ) or ""
            meli_shipping_logistic_type and fields.update({'meli_shipping_logistic_type': meli_shipping_logistic_type })
            bindT.write(fields)

            for bind in bindT.variant_bindings:
                bind.copy_from_rjson( rjson=rjson, meli=meli )

            seller_sku = product_tmpl_id.product_variant_ids.mapped("default_code") or ("seller_sku" in rjson and rjson["seller_sku"]) or product_tmpl_id.default_code
            barcode = product_tmpl_id.product_variant_ids.mapped("barcode") or ("barcode" in rjson and rjson["barcode"]) or product_tmpl_id.barcode
            fields = {'sku': seller_sku or "",'barcode': barcode or ""}
            bindT.write(fields)


    def fetch_meli_product( self, meli = None, rjson = None, from_meli_oerp = False, fetch_variants = False ):
        _logger.info("binding template fetch_meli_product")

        #fetch product full data from MELI into binding
        for bindT in self:

            account = bindT.connection_account
            meli_id = bindT.conn_id
            productT = bindT.product_tmpl_id

            if not meli:
                meli = self.env['meli.util'].get_new_instance( account.company_id, account )

            if not meli_id or not meli:
                continue;

            if from_meli_oerp: #TODO, check validity and meli_id in bindT.product_tmpl_id.meli_ids:
                bindT.copy_from_meli_oerp()
            else:
                rjson = rjson or account.fetch_meli_product( meli_id=meli_id, meli=meli )
                bindT.copy_from_rjson( rjson=rjson, meli=meli )

            if fetch_variants:
                pv_bindings = self.env["mercadolibre.product"].search([("conn_id","=",meli_id),
                                                                        ("binding_product_tmpl_id","=",bindT.id),
                                                                        ("connection_account","=",account.id)])
                if pv_bindings:
                    _logger.info("Binding template fetch_meli_product >> Fetching variants pv_bindings: "+str(len(pv_bindings)))
                    for pv_bind in pv_bindings:
                        try:
                            pv_bind.fetch_meli_product( meli = meli, rjson = rjson, from_meli_oerp = from_meli_oerp )
                        except:
                            _logger.error("Error fetching variant product binding: "+str(pv_bind))
                else:
                    _logger.error("Missing variant bindings to fetch meli data")


    def product_meli_status_put( self, context=None, status=None, meli=False):

        company = self.env.user.company_id
        account = self.connection_account
        config = (account and account.configuration) or company
        company = ("company_id" in config._fields and config.company_id) or company

        meli_id = self.conn_id
        if not meli:
            meli = self.env['meli.util'].get_new_instance(company, account)

            if meli.need_login():
                return meli.redirect_login()

        if meli_id and status and (status in ['paused','closed','active']):
            response = meli.put("/items/"+str(meli_id), { 'status': status }, {'access_token':meli.access_token})
            if response:
                _logger.info(response.json())
        else:
            _logger.error("Undefined status set, meli_id: "+str(meli_id)+" status: "+str(status))
        return {}

    def product_meli_status_close( self, context=None, meli=False ):
        _logger.info("MercadoLibre Product Tpl product_meli_status_close")
        return self.product_meli_status_put(context=context,status='closed',meli=meli)

    def product_meli_status_pause( self, context=None, meli=False ):
        _logger.info("MercadoLibre Product Tpl product_meli_status_pause")
        return self.product_meli_status_put(context=context,status='paused',meli=meli)

    def product_meli_status_active( self, context=None, meli=False ):
        _logger.info("MercadoLibre Product Tpl product_meli_status_active")
        return self.product_meli_status_put(context=context,status='active',meli=meli)

    def product_meli_delete( self, context=None, meli=False ):
        _logger.info("MercadoLibre Product Tpl product_meli_delete")
        company = self.env.user.company_id
        account = self.connection_account
        config = (account and account.configuration) or company
        company = ("company_id" in config._fields and config.company_id) or company

        meli_id = self.conn_id

        if not meli:
            meli = self.env['meli.util'].get_new_instance(company, account)
        if meli.need_login():
            return meli.redirect_login()

        if meli_id:
            response = meli.put("/items/"+str(meli_id), { 'deleted': 'true' }, {'access_token':meli.access_token})

            rjson = response.json()
            _logger.info( rjson )
            ML_status = rjson["status"]
            if "error" in rjson:
                ML_status = rjson["error"]
            if "sub_status" in rjson:
                if len(rjson["sub_status"]) and rjson["sub_status"][0]=='deleted':
                    #product.write({ 'meli_id': '','meli_id_variation': '' })
                    _logger.info("Deleted ok: TODO: Delete template binding, and meli_id on base product...")

        return {}

    def product_template_stats(self):
        _logger.info("bind template >> product_template_stats")
        for bind in self:

            _pubs = ""
            _stats = ""

            product = bind.product_tmpl_id

            if product and 1==2:
                for variant in product.product_variant_ids:
                    if (variant.meli_pub):
                        if ( (variant.meli_status=="active" or variant.meli_status=="paused") and variant.meli_id):
                            ml_full_status = variant.meli_status
                            if (variant.meli_sub_status):
                                ml_full_status+= ' ('+str(variant.meli_sub_status)+')'
                            if (len(_pubs)):
                                _pubs = _pubs + "|" + variant.meli_id + ":" + ml_full_status
                            else:
                                _pubs = variant.meli_id + ":" + ml_full_status

                            if (variant.meli_status=="active"):
                                _stats = "active"

                            if (_stats == "" and variant.meli_status=="paused"):
                                _stats = "paused"

            #bind.meli_publications = _pubs
            bind.meli_variants_status = _stats

        return {}

    meli_variants_status = fields.Text(compute=product_template_stats,string='Meli Variant Status')

class MercadoLibreConnectionBindingProductVariant(models.Model):

    _name = "mercadolibre.product"
    _description = "MercadoLibre Product Binding Product"
    #_inherit = ["mercadolibre.product_template","ocapi.connection.binding.product"]
    _inherit = ["ocapi.connection.binding.product"]

    connection_account = fields.Many2one( "mercadolibre.account", string="MercadoLibre Account" )
    binding_product_tmpl_id = fields.Many2one("mercadolibre.product_template",string="Product Template Binding")

    image_bindings = fields.One2many('mercadolibre.product.image', "binding_product_variant_id", string="Product Variant Images")

    def product_get_meli_update( self ):

        _logger.info("bind variant >> product_get_meli_update")

        warningobj = self.env['warning']
        product_obj = self.env['product.product']

        ML_status = "unknown"
        ML_sub_status = ""
        ML_permalink = ""
        ML_state = False
        #meli = None

        for product in self:

            account = product.connection_account
            company = (account and account.company_id) or self.env.user.company_id
            meli = self.env['meli.util'].get_new_instance( company, account )
            if meli.need_login():
                ML_status = "unknown"
                ML_permalink = ""
                ML_state = True

            if product.conn_id and not product.meli_id:
                product.meli_id = product.conn_id

            if product.meli_id and not meli.need_login():
                response = meli.get( "/items/"+product.meli_id, { 'access_token': meli.access_token } )
                rjson = response.json()
                if "status" in rjson:
                    ML_status = rjson["status"]
                if "permalink" in rjson:
                    ML_permalink = rjson["permalink"]
                if "error" in rjson:
                    ML_status = rjson["error"]
                    ML_permalink = ""
                if "sub_status" in rjson:
                    if len(rjson["sub_status"]):
                        ML_sub_status =  rjson["sub_status"][0]
                        if ( ML_sub_status =='deleted' ):
                            product.write({ 'meli_id': '','meli_id_variation': '' })

            product.meli_status = ML_status
            product.meli_sub_status = ML_sub_status
            product.meli_permalink = ML_permalink
            product.meli_state = ML_state

#    meli_pub_variant_attributes = fields.Many2many(prod_att_line, relation='meli_pub_variant_attributes',column1='ml_template_id',column2='att_line_id', string='Atributos a publicar en ML',help='Seleccionar los atributos a publicar')

    #typical values
    meli_title = fields.Char(string='Nombre del producto en Mercado Libre',size=256)
    meli_description = fields.Text(string='Descripción')
    meli_category = fields.Many2one("mercadolibre.category","Categoría de MercadoLibre")
    meli_price = fields.Char(string='Precio de venta', size=128)
    meli_dimensions = fields.Char( string="Dimensiones del producto", size=128)
    meli_pub = fields.Boolean('Meli Publication',help='MELI Product',index=True)

    meli_buying_mode = fields.Selection( [("buy_it_now","Compre ahora"),("classified","Clasificado")], string='Método de compra')
    meli_currency = fields.Selection([("ARS","Peso Argentino (ARS)"),
                                        ("MXN","Peso Mexicano (MXN)"),
                                        ("COP","Peso Colombiano (COP)"),
                                        ("PEN","Sol Peruano (PEN)"),
                                        ("BOB","Boliviano (BOB)"),
                                        ("BRL","Real (BRL)"),
                                        ("CLP","Peso Chileno (CLP)"),
                                        ("CRC","Colon Costarricense (CRC)"),
                                        ("UYU","Peso Uruguayo (UYU)"),
                                        ("USD","Dolar Estadounidense (USD)")],
                                        string='Moneda')
    meli_condition = fields.Selection([ ("new", "Nuevo"), ("used", "Usado"), ("not_specified","No especificado")],'Condición del producto')
    meli_warranty = fields.Char(string='Garantía', size=256)
    meli_listing_type = fields.Selection([("free","Libre"),("bronze","Bronce"),("silver","Plata"),("gold","Oro"),("gold_premium","Gold Premium"),("gold_special","Gold Special/Clásica"),("gold_pro","Oro Pro")], string='Tipo de lista')

    #post only fields
    meli_post_required = fields.Boolean(string='Publicable', help='Este producto es publicable en Mercado Libre')

    #TODO deprecated
    meli_id = fields.Char(string='ML Id', help='Id del item asignado por Meli', size=256, index=True)
    meli_description_banner_id = fields.Many2one("mercadolibre.banner","Banner")

    meli_buying_mode = fields.Selection(string='Método',help='Método de compra',selection=[("buy_it_now","Compre ahora"),("classified","Clasificado")])
    meli_price = fields.Char( string='Precio',help='Precio de venta en ML', size=128)
    meli_price_fixed = fields.Boolean(string='Price is fixed')
    meli_available_quantity = fields.Integer(string='Cantidades', help='Cantidad disponible a publicar en ML')
    meli_imagen_logo = fields.Char(string='Imagen Logo', size=256)
    meli_imagen_id = fields.Char(string='Imagen Id', size=256)
    meli_imagen_link = fields.Char(string='Imagen Link', size=256)
    meli_imagen_hash = fields.Char(string='Imagen Hash')
    meli_multi_imagen_id = fields.Char(string='Multi Imagen Ids', size=512)
    meli_video = fields.Char( string='Video (id de youtube)', size=256)

    meli_permalink = fields.Char( compute=product_get_meli_update, size=256, string='Link',help='PermaLink in MercadoLibre', store=False )
    meli_state = fields.Boolean( compute=product_get_meli_update, string='Login',help="Inicio de sesión requerida", store=False )
    meli_status = fields.Char( compute=product_get_meli_update, size=128, string='Status', help="Estado del producto en ML", store=False )
    meli_sub_status = fields.Char( compute=product_get_meli_update, size=128, string='Sub status',help="Sub Estado del producto en ML", store=False )

    meli_last_status = fields.Char( string="Last Status",index=True )

    meli_attributes = fields.Text(string='Atributos')

    meli_model = fields.Char(string="Modelo",size=256)
    meli_brand = fields.Char(string="Marca",size=256)
    meli_default_stock_product = fields.Many2one("product.product","Producto de referencia para stock")

    #TODO deprecated
    meli_id_variation = fields.Char( string='Variation Id',help='Id de Variante de Meli', size=256)

    meli_catalog_listing = fields.Boolean(string='Catalog Listing', size=256)
    meli_catalog_product_id = fields.Char(string='Catalog Product Id', size=256)
    meli_catalog_item_relations = fields.Char(string='Catalog Item Relations', size=256)
    meli_catalog_automatic_relist = fields.Boolean(string='Catalog Auto Relist', size=256)

    meli_shipping_logistic_type = fields.Char(string="Logistic Type",index=True)

    meli_inventory_id = fields.Char(string="Inventory Id",index=True)

    def copy_from_meli_oerp( self ):
        for bind in self:
            product = bind.product_id
            _logger.info("variant bind copy_from_meli_oerp meli_id: %s meli_id_variation: %s" % (str(bind.conn_id),str(bind.conn_variation_id)))
            _logger.info("variant bind copy_from_meli_oerp p.meli_id: %s p.meli_id_variation: %s" % (str(product.meli_id),str(product.meli_id_variation)))
            if (product.meli_id_variation!=bind.conn_variation_id):
                pb2 = self.env["mercadolibre.product"].search([ ('conn_id','=',product.meli_id),
                                                          ('conn_variation_id','=',product.meli_id_variation),
                                                          ('product_tmpl_id','=',bind.product_tmpl_id),
                                                          ('connection_account','=',bind.connection_account.id)])
                if pb2:
                    _logger.info("Look! Duplicates for: "+str(product.meli_id_variation))
                    return

            #id assignation
            bind.meli_id = product.meli_id
            bind.meli_id_variation = product.meli_id_variation
            bind.conn_id = product.meli_id
            bind.conn_variation_id = product.meli_id_variation

            #TODO: sku assign?
            bind.sku = product.default_code
            bind.barcode = product.barcode

            #basic info
            bind.meli_title = product.meli_title
            bind.meli_description = product.meli_description
            bind.meli_category = product.meli_category
            bind.meli_price = product.meli_price
            bind.price = product.meli_price
            bind.stock = product.meli_available_quantity
            bind.meli_available_quantity = product.meli_available_quantity

            bind.meli_shipping_logistic_type = product.meli_shipping_logistic_type

            #attributes
            bind.meli_attributes = product.meli_attributes
            bind.meli_model = product.meli_model
            bind.meli_brand = product.meli_brand

            #publish ref info
            bind.meli_pub = product.meli_pub
            #bind.meli_master = product.meli_master
            #bind.meli_ids = product.meli_ids

            #config info
            bind.meli_currency = product.meli_currency
            bind.meli_condition = product.meli_condition
            bind.meli_warranty = product.meli_warranty
            bind.meli_listing_type = product.meli_listing_type
            bind.meli_dimensions = product.meli_dimensions

    def copy_from_rjson( self, rjson, meli=None ):
        #copia correctamente el sku correspondiente al conn_variation_id
        #conn_variation_id debe setearse al traer el producto ?
        _logger.info("variant bind >> copy_from_rjson")
        if not rjson:
            return

        for bind in self:
            account = bind.connection_account
            config = account.configuration
            #productT = bindT.product_tmpl_id
            #basic info
            catid, wwwid = self.env["mercadolibre.category"].meli_get_category( rjson['category_id'], meli=meli, create_missing_website=config.mercadolibre_create_website_categories )
            desplain = ("description" in rjson and rjson["description"]) or ""
            seller_sku = None
            barcode = None
            variant_stock = 0
            if "variations" in rjson and len(rjson["variations"]):
                for var in rjson["variations"]:
                    if not "id" in var:
                        _logger.error(var)
                    if ("id" in var and str(var["id"]) == str(bind.conn_variation_id) ):
                        _logger.info("FOUNDED!!!")
                        seller_sku = ("seller_sku" in var and var["seller_sku"]) or ""
                        barcode = ("barcode" in var and var["barcode"]) or ""
                        variant_stock = ("available_quantity" in var and var["available_quantity"])
                if not seller_sku:
                    _logger.error("seller sku not found: meli_id: "+str(bind.conn_id)+" varid: "+str(bind.conn_variation_id))
            if not seller_sku:
                seller_sku = ("seller_sku" in rjson and rjson["seller_sku"]) or ""
            if not barcode:
                barcode = ("barcode" in rjson and rjson["barcode"]) or ""
            fields = {
                'meli_permalink': rjson['permalink'],
                'meli_title': rjson['title'].encode("utf-8"),
                'meli_description': desplain,
                'meli_listing_type': rjson['listing_type_id'],
                'meli_buying_mode':rjson['buying_mode'],
                'meli_price': str(rjson['price']),
                'price': str(rjson['price']),
                'meli_available_quantity': variant_stock,
                'stock': variant_stock,
                'meli_currency': rjson['currency_id'],
                'meli_condition': rjson['condition'],
                #'meli_available_quantity': rjson['available_quantity'],
                'meli_warranty': rjson['warranty'],
                'meli_category': catid,
                'meli_id': rjson["id"],
                'sku': seller_sku or '',
                'barcode': barcode or '',
                'meli_id_variation': bind.conn_variation_id,
                #'meli_imagen_link': rjson['thumbnail'],
                #'meli_video': str(vid),
                #'meli_dimensions': meli_dim_str,
            }
            meli_shipping_logistic_type = ( rjson and "shipping" in rjson and "logistic_type" in rjson["shipping"] and rjson["shipping"]["logistic_type"] ) or ""
            meli_shipping_logistic_type and fields.update({'meli_shipping_logistic_type': meli_shipping_logistic_type })

            _logger.info("variant bind >> copy_from_rjson: var id: "+str(fields["meli_id_variation"])+" sku: "+str(fields["sku"])+" barcode: "+str(fields["barcode"]) )
            bind.write(fields)

    def fetch_meli_product( self, meli = None, rjson = None, from_meli_oerp=False ):
        _logger.info("binding variant fetch_meli_product")

        #fetch product full data from MELI into binding
        for bind in self:

            account = bind.connection_account
            meli_id = bind.conn_id
            meli_id_variation = bind.conn_variation_id

            if not meli:
                meli = self.env['meli.util'].get_new_instance( account.company_id, account )

            if not meli_id or not meli:
                continue;

            if from_meli_oerp: #TODO, check validity and meli_id in bindT.product_tmpl_id.meli_ids:
                bind.copy_from_meli_oerp()
            else:
                rjson = rjson or account.fetch_meli_product( meli_id=meli_id, meli=meli )
                bind.copy_from_rjson( rjson=rjson, meli=meli )

    def product_post( self, meli=None ):
        _logger.info("MercadoLibre Bind Product Post")
        result = []
        for bind in self:

            product = bind.product_id
            account = bind.connection_account
            meli_id = bind.conn_id
            meli_id_variation = bind.conn_variation_id

            if not meli:
                meli = self.env['meli.util'].get_new_instance( account.company_id, account )

            if not meli_id or not meli:
                continue;

            if product:
                res = product.product_post( bind=self, meli=meli, config=account.configuration )
                result.append(res)
        _logger.info( "result: " + str(result) )
        return result

    def product_update( self ):
        _logger.info("meli_oerp_multiple >> MercadoLibre Product Binding Update")

    #def category_predictor( self ):
    #    _logger.info("MercadoLibre Product template Category Predictor")
    def product_meli_get_product( self, meli=None, rjson=None ):

        _logger.info("meli_oerp_multiple >> product_meli_get_product >> (Binding) MercadoLibre Product product_meli_get_product")

        for bind in self:

            account = bind.connection_account
            product = bind.product_id
            product_template = bind.product_tmpl_id
            meli_id = bind.conn_id
            meli_id_variation = bind.conn_variation_id

            if not meli:
                meli = self.env['meli.util'].get_new_instance( account.company_id, account )

            rjson = rjson or account.fetch_meli_product( meli_id=meli_id, meli=meli )
            meli_oerp_match_import = (product.meli_id and meli_id and product.meli_id==meli_id)
            bind_only = (meli_oerp_match_import==False) #just bind
            #TODO: recheck to not import ML to Odoo Product if this is not the principal bind conn_id
            if (not product.meli_id or meli_oerp_match_import):
                _logger.info("product_meli_get_product: bind_only: "+str(bind_only))
                res = product.product_meli_get_product( meli_id=meli_id, account=account, meli=meli, rjson=rjson )
                _logger.info("variant get product >> product_meli_get_product res:"+str(res))
                if res and "error" in res:
                    _logger.error(res)
                    return res

            #TODO: recheck bindings for this product and this binding
            if (product_template):
                bindT = product_template.mercadolibre_bind_to( account=account, meli_id=meli_id, bind_variants=True, meli=meli, rjson=rjson, bind_only=bind_only )
                if bindT:
                    # from_meli_oerp = True copy form recent imported
                    bindT.fetch_meli_product( meli=meli, from_meli_oerp=False, fetch_variants=True, rjson=rjson )

    def action_category_predictor( self ):
        _logger.info("MercadoLibre Product action_category_predictor")

    def product_post_stock( self, context=None, meli=None ):
        #_logger.info("MercadoLibre Product product_post_stock: context: "+str(context))
        for bindv in self:

            account = bindv.connection_account
            config = account and account.configuration
            product = bindv.product_id
            product_template = bindv.product_tmpl_id
            meli_id = bindv.conn_id
            meli_id_variation = bindv.conn_variation_id

            if not product or not product_template:
                continue;

            if not meli:
                meli = self.env['meli.util'].get_new_instance( account.company_id, account )

            #
            try:
                _logger.info("mercadolibre.product product_post_stock")
                #one variant bind from variant product
                bindv.meli_available_quantity = product._meli_available_quantity( meli_id=meli_id, meli=meli, config=config)
                bindv.stock = bindv.meli_available_quantity
                if bindv.meli_inventory_id:
                    logistic_type = bindv.product_id._meli_update_logistic_type(meli_id=meli_id, meli=meli,config=config)
                    if logistic_type and logistic_type in ["fulfillment"]:
                        bindv.stock_update = ml_datetime( str( datetime.now() ) )
                        res = { "error": "fulfillment"}
                        bindv.stock_error = str(res)
                        _logger.info(bindv.stock_error)
                        return res
                res = product.x_product_post_stock( context=context, meli=meli, config=config, meli_id=meli_id, meli_id_variation=meli_id_variation, target=bindv )
                if res and 'error' in res:
                    if 'fulfillment' in str(res):
                        bindv.meli_inventory_id = "fetch"
                    bindv.stock_error = str(res)
                    bindv.stock_update = ml_datetime( str( datetime.now() ) )
                    return res
                bindv.meli_inventory_id = None
                #more than one
                bindv.stock_error = "Ok"
                bindv.stock_update = ml_datetime( str( datetime.now() ) )

            except Exception as e:
                _logger.info("mercadolibre.product product_post_stock > exception error")
                _logger.info(e, exc_info=True)
                pass;

            return {}

    def product_post_price( self, context=None, meli=None ):
        _logger.info("MercadoLibre Product product_post_price: context: "+str(context))
        for bindv in self:

            account = bindv.connection_account
            config = account and account.configuration
            product = bindv.product_id
            product_template = bindv.product_tmpl_id
            meli_id = bindv.conn_id
            meli_id_variation = bindv.conn_variation_id

            if not product or not product_template:
                continue;

            if not meli:
                meli = self.env['meli.util'].get_new_instance( account.company_id, account )

            #
            try:
                _logger.info("mercadolibre.product product_post_price")
                #one variant bind from variant product
                bindv.meli_price = product.set_meli_price()
                bindv.price = bindv.meli_price

                res = product.x_product_post_price( context=context, meli=meli, config=config, meli_id=meli_id, meli_id_variation=meli_id_variation )
                if res and 'error' in res:
                    return res
                bindv.price_update = ml_datetime( str( datetime.now() ) )
                #more than one

            except Exception as e:
                _logger.info("mercadolibre.product product_post_stock > exception error")
                _logger.info(e, exc_info=True)
                pass;

            return {}

    def product_meli_status_put( self, context=None, status=None, meli=False):

        company = self.env.user.company_id
        account = self.connection_account
        config = (account and account.configuration) or company
        company = ("company_id" in config._fields and config.company_id) or company

        meli_id = self.conn_id
        if not meli:
            meli = self.env['meli.util'].get_new_instance(company, account)

            if meli.need_login():
                return meli.redirect_login()

        if meli_id and status and (status in ['paused','closed','active']):
            response = meli.put("/items/"+str(meli_id), { 'status': status }, {'access_token':meli.access_token})
            if response:
                _logger.info(response.json())
        else:
            _logger.error("Undefined status set, meli_id: "+str(meli_id)+" status: "+str(status))
        return {}

    def product_meli_status_close( self, context=None, meli=False ):
        _logger.info("MercadoLibre Product product_meli_status_close")
        return self.product_meli_status_put(context=context,status='closed',meli=meli)

    def product_meli_status_pause( self, context=None, meli=False ):
        _logger.info("MercadoLibre Product product_meli_status_pause")
        return self.product_meli_status_put(context=context,status='paused',meli=meli)

    def product_meli_status_active( self, context=None, meli=False ):
        _logger.info("MercadoLibre Product product_meli_status_active")
        return self.product_meli_status_put(context=context,status='active',meli=meli)

    def product_meli_delete( self, context=None, meli=False ):
        _logger.info("MercadoLibre Product product_meli_delete")
        company = self.env.user.company_id
        account = self.connection_account
        config = (account and account.configuration) or company
        company = ("company_id" in config._fields and config.company_id) or company

        meli_id = self.conn_id

        if not meli:
            meli = self.env['meli.util'].get_new_instance(company, account)
        if meli.need_login():
            return meli.redirect_login()

        if meli_id:
            response = meli.put("/items/"+str(meli_id), { 'deleted': 'true' }, {'access_token':meli.access_token})

            rjson = response.json()
            _logger.info( rjson )
            ML_status = rjson["status"]
            if "error" in rjson:
                ML_status = rjson["error"]
            if "sub_status" in rjson:
                if len(rjson["sub_status"]) and rjson["sub_status"][0]=='deleted':
                    #product.write({ 'meli_id': '','meli_id_variation': '' })
                    _logger.info("Deleted ok: TODO: Delete variant binding, and meli_id on base product...")

        return {}

    def product_meli_upload_image( self ):
        _logger.info("MercadoLibre Product product_meli_upload_image")

    def product_meli_login( self ):
        _logger.info("MercadoLibre Product product_meli_login")

class MercadoLibreConnectionBindingSaleOrderPayment(models.Model):

    _name = "mercadolibre.payment"
    _description = "MercadoLibre Sale Order Payment Binding"
    _inherit = ["ocapi.binding.payment","mercadolibre.payments"]

    order_id = fields.Many2one("mercadolibre.sale_order",string="Order")
    connection_account = fields.Many2one( "mercadolibre.account", string="MercadoLibre Account" )
    name = fields.Char(string="Payment Name")

    meli_oerp_payment = fields.Many2one( "mercadolibre.payments",string="Payment from meli_oerp")

    def _get_ml_journal(self):
        journal_id = None
        #journal_id = self.env.user.company_id.mercadolibre_process_payments_journal
        #if not journal_id:
        #    journal_id = self.env['account.journal'].search([('code','=','ML')])
        #if not journal_id:
        #    journal_id = self.env['account.journal'].search([('code','=','MP')])
        return journal_id

    def _get_ml_partner(self):
        partner_id = None
        #partner_id = self.env.user.company_id.mercadolibre_process_payments_res_partner
        #if not partner_id:
        #    partner_id = self.env['res.partner'].search([('ref','=','MELI')])
        #if not partner_id:
        #    partner_id = self.env['res.partner'].search([('name','=','MercadoLibre')])
        return partner_id

    def _get_ml_customer_partner(self):
        sale_order = self._get_ml_customer_order()
        return (sale_order and sale_order.partner_id)

    def _get_ml_customer_order(self):
        mlorder = self.order_id
        mlshipment = mlorder.shipment
        return (mlorder and mlorder.sale_order) or (mlshipment and mlshipment.sale_order)

    def create_payment(self):
        self.ensure_one()
        if self.account_payment_id:
            raise ValidationError('Ya esta creado el pago')
        if self.status != 'approved':
            return None
        journal_id = self._get_ml_journal()
        payment_method_id = self.env['account.payment.method'].search([('code','=','electronic'),('payment_type','=','inbound')])
        if not journal_id or not payment_method_id:
            raise ValidationError('Debe configurar el diario/metodo de pago')
        partner_id = self._get_ml_customer_partner()
        currency_id = self.env['res.currency'].search([('name','=',self.currency_id)])
        if not currency_id:
            raise ValidationError('No se puede encontrar la moneda del pago')

        communication = self.payment_id
        if self._get_ml_customer_order():
            communication = ""+str(self._get_ml_customer_order().name)+" OP "+str(self.payment_id)+str(" TOT")

        vals_payment = {
                'partner_id': partner_id.id,
                'payment_type': 'inbound',
                'payment_method_id': payment_method_id.id,
                'journal_id': journal_id.id,
                'meli_payment_id': self.id,
                'communication': communication,
                'currency_id': currency_id.id,
                'partner_type': 'customer',
                'amount': self.total_paid_amount,
                }
        acct_payment_id = self.env['account.payment'].create(vals_payment)
        acct_payment_id.post()
        self.account_payment_id = acct_payment_id.id

    def create_supplier_payment(self):
        self.ensure_one()
        if self.status != 'approved':
            return None
        if self.account_supplier_payment_id:
            raise ValidationError('Ya esta creado el pago')
        journal_id = self._get_ml_journal()
        payment_method_id = self.env['account.payment.method'].search([('code','=','outbound_online'),('payment_type','=','outbound')])
        if not journal_id or not payment_method_id:
            raise ValidationError('Debe configurar el diario/metodo de pago')
        partner_id = self._get_ml_partner()
        if not partner_id:
            raise ValidationError('No esta dado de alta el proveedor MercadoLibre')
        currency_id = self.env['res.currency'].search([('name','=',self.currency_id)])
        if not currency_id:
            raise ValidationError('No se puede encontrar la moneda del pago')

        communication = self.payment_id
        if self._get_ml_customer_order():
            communication = ""+str(self._get_ml_customer_order().name)+" OP "+str(self.payment_id)+str(" FEE")

        vals_payment = {
                'partner_id': partner_id.id,
                'payment_type': 'outbound',
                'payment_method_id': payment_method_id.id,
                'journal_id': journal_id.id,
                'meli_payment_id': self.id,
                'communication': communication,
                'currency_id': currency_id.id,
                'partner_type': 'supplier',
                'amount': self.fee_amount,
                }
        acct_payment_id = self.env['account.payment'].create(vals_payment)
        acct_payment_id.post()
        self.account_supplier_payment_id = acct_payment_id.id

    def create_supplier_payment_shipment(self):
        self.ensure_one()
        if self.status != 'approved':
            return None
        if self.account_supplier_payment_shipment_id:
            raise ValidationError('Ya esta creado el pago')
        journal_id = self._get_ml_journal()
        payment_method_id = self.env['account.payment.method'].search([('code','=','outbound_online'),('payment_type','=','outbound')])
        if not journal_id or not payment_method_id:
            raise ValidationError('Debe configurar el diario/metodo de pago')
        partner_id = self._get_ml_partner()
        if not partner_id:
            raise ValidationError('No esta dado de alta el proveedor MercadoLibre')
        currency_id = self.env['res.currency'].search([('name','=',self.currency_id)])
        if not currency_id:
            raise ValidationError('No se puede encontrar la moneda del pago')
        if (not self.order_id or not self.order_id.shipping_list_cost>0.0):
            raise ValidationError('No hay datos de costo de envio')

        communication = self.payment_id
        if self._get_ml_customer_order():
            communication = ""+str(self._get_ml_customer_order().name)+" OP "+str(self.payment_id)+str(" SHP")

        vals_payment = {
                'partner_id': partner_id.id,
                'payment_type': 'outbound',
                'payment_method_id': payment_method_id.id,
                'journal_id': journal_id.id,
                'meli_payment_id': self.id,
                'communication': communication,
                'currency_id': currency_id.id,
                'partner_type': 'supplier',
                'amount': self.order_id.shipping_list_cost,
                }
        acct_payment_id = self.env['account.payment'].create(vals_payment)
        acct_payment_id.post()
        self.account_supplier_payment_shipment_id = acct_payment_id.id

class MercadoLibreConnectionBindingSaleOrderShipmentItem(models.Model):

    _name = "mercadolibre.shipment.item"
    _description = "Ocapi Sale Order Shipment Item"
    _inherit = "ocapi.binding.shipment.item"

    connection_account = fields.Many2one( "mercadolibre.account", string="MercadoLibre Account" )
    shipping_id = fields.Many2one("mercadolibre.bind_shipment",string="Shipment")
    product = fields.Char(string="Product Id")
    variation = fields.Char(string="Variation Id")
    quantity = fields.Float(string="Quantity")

class MercadoLibreConnectionBindingSaleOrderShipment(models.Model):

    _name = "mercadolibre.bind_shipment"
    _description = "Ocapi Sale Order Shipment Binding"
    _inherit = ["ocapi.binding.shipment","mercadolibre.shipment"]

    connection_account = fields.Many2one( "mercadolibre.account", string="MercadoLibre Account" )

    order_id = fields.Many2one("mercadolibre.sale_order",string="Order")
    products = fields.One2many("mercadolibre.shipment.item", "shipping_id", string="Product Items")

class MercadoLibreConnectionBindingSaleOrderClient(models.Model):

    _name = "mercadolibre.client"
    _description = "MercadoLibre Client Binding"
    _inherit = ["ocapi.binding.client","mercadolibre.buyers"]

    def get_display_name(self):
        for client in self:
            client.display_name = str(client.contactPerson)+" ["+str(client.name)+"]"

    display_name = fields.Char(string="Display Name",store=False,compute=get_display_name)
    connection_account = fields.Many2one( "mercadolibre.account", string="MercadoLibre Account" )

class MercadoLibreConnectionBindingSaleOrderLine(models.Model):

    _name = "mercadolibre.sale_order_line"
    _description = "MercadoLibre Sale Order Line Binding"
    _inherit = ["ocapi.binding.sale_order_line", "mercadolibre.order_items" ]

    connection_account = fields.Many2one( "mercadolibre.account", string="MercadoLibre Account" )
    order_id = fields.Many2one("mercadolibre.sale_order",string="Order")

class MercadoLibreConnectionBindingSaleOrder(models.Model):

    _name = "mercadolibre.sale_order"
    _description = "MercadoLibre Sale Order Binding Sale"
    _inherit = ["ocapi.binding.sale_order","mercadolibre.orders"]

    connection_account = fields.Many2one( "mercadolibre.account", string="MercadoLibre Account" )
    mercadolibre_old_order = fields.Many2one( "mercadolibre.orders", string="MercadoLibre Old Order" )
    client = fields.Many2one("mercadolibre.client",string="Client",index=True)

    lines = fields.One2many("mercadolibre.sale_order_line","order_id", string="Order Items")
    payments = fields.One2many("mercadolibre.payment","order_id",string="Order Payments")
    shipments = fields.One2many("mercadolibre.shipment","order_id",string="Order Shipments")


    def orders_query_iterate( self, offset=0, account=None, meli=None, context=None ):

        offset_next = 0

        account = account or self.connection_account
        company = (account and account.company_id) or self.env.user.company_id
        config = account.configuration or company
        context = context or self.env.context

        orders_obj = self.env['mercadolibre.sale_order']

        if not meli:
            meli = self.env['meli.util'].get_new_instance(company, account)

        orders_query = "/orders/search?seller="+meli.seller_id+"&sort=date_desc"
        #TODO: "create parameter for": orders_query+= "&limit=10"

        if (offset):
            orders_query = orders_query + "&offset="+str(offset).strip()

        response = meli.get( orders_query, {'access_token':meli.access_token})
        orders_json = response.json()

        if "error" in orders_json:
            _logger.error( orders_query )
            _logger.error( orders_json["error"] )
            if (orders_json["message"]=="invalid_token"):
                _logger.error( orders_json["message"] )
            return {}

        order_date_filter = ("mercadolibre_filter_order_datetime" in config._fields and config.mercadolibre_filter_order_datetime)

        if "paging" in orders_json:
            if "total" in orders_json["paging"]:
                if (orders_json["paging"]["total"]==0):
                    return {}
                else:
                    if (orders_json["paging"]["total"]>=(offset+orders_json["paging"]["limit"])):
                        if not order_date_filter:
                            offset_next = 0
                        else:
                            offset_next = offset + orders_json["paging"]["limit"]
                        _logger.info("offset_next:"+str(offset_next))

        if "results" in orders_json:
            for order_json in orders_json["results"]:
                if order_json:
                    #_logger.info( order_json )
                    pdata = {"id": False, "order_json": order_json}
                    try:
                        self.orders_update_order_json( data=pdata, config=config, meli=meli )
                        self._cr.commit()
                    except Exception as e:
                        _logger.error("orders_query_iterate > Error actualizando ORDEN")
                        _logger.error(e, exc_info=True)
                        pass

        if (offset_next>0):
            self.orders_query_iterate(offset=offset_next, account=account, meli=meli)

        return {}

    def orders_query_recent( self, account=None, meli=None, context=None ):

        context = context or self.env.context
        account = account or self.connection_account

        _logger.info("mercadolibre.sale_order >> orders_query_recent("+str(account)+","+str(meli)+") context: " + str(context))
        if not account:
            return {}

        company = (account and account.company_id) or self.env.user.company_id
        config = account.configuration or company

        if not meli:
            meli = self.env['meli.util'].get_new_instance(company, account)

        if 1==1:
            _logger.info("mercadolibre.sale_order >> recall mercadolibre.orders >> orders_query_recent")
            self.env['mercadolibre.orders'].orders_query_recent( meli=meli, config=account.configuration )
            return {}

        self._cr.autocommit(False)

        try:
            self.orders_query_iterate( 0, account )
        except Exception as e:
            _logger.info("orders_query_recent > Error iterando ordenes")
            _logger.error(e, exc_info=True)
            self._cr.rollback()

        return {}

#class MercadoLibreConnectionBindingProductCategory(models.Model):

#    _name = "mercadolibre.category"
#    _description = "MercadoLibre Binding Category"
#    _inherit = "ocapi.binding.category"

#    connection_account = fields.Many2one( "mercadolibre.account", string="MercadoLibre Account" )

#    name = fields.Char(string="Category",index=True)
#    category_id = fields.Char(string="Category Id",index=True)
