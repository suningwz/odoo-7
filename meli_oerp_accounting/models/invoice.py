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
import logging

import json

import logging
_logger = logging.getLogger(__name__)

from dateutil.parser import *
from datetime import *
from urllib.request import urlopen
import requests
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


import base64
from odoo.addons.meli_oerp.models.versions import *

#https://developers.mercadolibre.com.co/es_ar/cargar-factura

#curl -X POST https://api.mercadolibre.com/packs/$PACK_ID/fiscal_documents?access_token=$ACCESS_TOKEN
#-H 'Content-Type: multipart/form-data' \
#-F 'fiscal_document=@/home/user/.../Factura_adjunta.pdf'

#curl -X POST https://api.mercadolibre.com/packs/$PACK_ID/fiscal_documents?access_token=$ACCESS_TOKEN
#  -H 'content-type: multipart/form-data;'
#  -F 'fiscal_document=@/home/user/.../Factura_adjunta.pdf'
#  -F 'fiscal_document=@/home/user/.../Factura_adjunta.xml'

#https://api.mercadolibre.com/packs/2000001921401367/fiscal_documents?access_token=APP_USR-6630319130713446-021014-a71d1e5701c937af631cabdb0bf0c5c3-115266467#json

"""
							<button name='orders_post_invoice' type="object"
								string="Publicar Facturas"
								attrs="{'invisible':[('invoice_posted','=',True)]}"
								class="oe_stat_button"
								icon="fa-globe"/>
							<field name="invoice_posted"/>
							<field name="invoice_fiscal_documents"/>
"""

class Invoice(models.Model):

    _inherit = acc_inv_model

    #@api.multi
    def firmar_factura_electronica(self):
        _logger.info("meli_oerp: firmar_factura_electronica")
        try:
            res = super( Invoice, self ).firmar_factura_electronica()
            sorder = self.env['sale.order'].search([('name','=',self.origin)], limit=1)
            if sorder:
                if sorder and sorder.meli_orders:
                    sorder.meli_orders[0].orders_post_invoice()

        except Exception as e:
            raise e;


    def crear_facturas( self ):
        #
        _logger.info("Crear Facturas")

        XMLname = None
        XMLbytes = None

        PDFName = None
        PDFbytes = None
        #zip_content = BytesIO()
        #zip_content.write(base64.b64decode(self.attachment_file))

        #zip_file.writestr(, zip_content.getvalue())

        #XMLbytes = base64.b64decode(self.attachment_file)
        if "attachment_file" in self._fields:
            XMLbytes = self.attachment_file
            XMLname = self.filename.replace('fv', 'ad').replace('nc', 'ad').replace('nd', 'ad') + '.xml'
            #_logger.info(XMLbytes)
            _logger.info(XMLname)

        if self.env.ref('l10n_co_cei.account_invoices_fe'):
            template = self.env.ref('l10n_co_cei.account_invoices_fe')
            render_template = template.render_qweb_pdf([self.id])
            #PDFbytes = base64.b64decode(base64.b64encode(render_template[0]))
            PDFbytes = base64.b64encode(render_template[0])
            PDFName = self.filename.replace('fv', 'ad').replace('nc', 'ad').replace('nd', 'ad') + '.pdf'
            #_logger.info(PDFbytes)
            _logger.info(PDFName)

        return XMLname, XMLbytes, PDFName, PDFbytes

class OrdersInvoice(models.Model):

    _inherit = "mercadolibre.orders"

    invoice_pdf = fields.Binary(string='Invoice PDF')
    invoice_xml = fields.Binary(string='Invoice XML')

    def orders_post_invoice(self, context=None, meli=None):
        context = context or self.env.context
        _logger.info("orders_post_invoice: context: "+str(context))

        self.invoice_posted = True

        _logger.info("Create binary PDF and XML for attach files")

        so = self.sale_order
        if so:
            invoices = self.env['account.invoice'].search([('origin','=',so.name)])
            #'estado_validacion': record['fe_approved'],
            respost = ""
            for inv in invoices:
                #chequear inv validacion
                #estado_dian = fields.Text(
                #    related="envio_fe_id.respuesta_validacion",
                #    copy=False
                #)
                if ('estado_dian' in inv._fields and ( inv.estado_dian and 'Procesado Correctamente' in inv.estado_dian) and inv.zipped_file):
                    _logger.info("Factura validada, generando.... para envio.")

                    XMLname, XMLbytes, PDFName, PDFbytes = inv.crear_facturas()

                    if PDFbytes:

                        self.invoice_pdf = PDFbytes
                    if XMLbytes:
                        self.invoice_xml = XMLbytes

                    files = []

                    if PDFName and PDFbytes and XMLname and XMLbytes:
                        files = [ ('fiscal_document', ( PDFName, base64.b64decode(PDFbytes), 'application/pdf')),
                                  ('fiscal_document', ( XMLname, base64.b64decode(XMLbytes), 'application/xml')) ]
                    elif PDFName and PDFbytes:
                        files = [ ('fiscal_document', ( PDFName, base64.b64decode(PDFbytes), 'application/pdf'))]
                    elif XMLname and XMLbytes:
                        files = [ ('fiscal_document', ( XMLName, base64.b64decode(XMLbytes), 'application/xml'))]

                    #files = [ ('fiscal_document', ( PDFName, base64.b64decode(PDFbytes), 'application/pdf')) ]
                    #files = [ ('fiscal_document', ( XMLname, base64.b64decode(XMLbytes), 'application/xml') ]
                    company = self.env.user.company_id
                    if not meli:
                        meli = self.env['meli.util'].get_new_instance(company)

                    if meli and files:
                        res = meli.uploadfiles("/packs/"+str(self.pack_id or self.order_id)+"/fiscal_documents", files=files, params={ "access_token": meli.access_token } )
                        _logger.info(res)
                        if res:
                            _logger.info(res.json())
                            respost += str(res.json())
                            #{'statusCode': 409, 'code': 'conflict', 'message': 'File Not allowed, the max amount of files already exist for the pack: 4433064137 and seller: 115266467', 'requestId': '557c88de-160f-4de9-a36d-2c01cb277ec6'}
                            if 'error' in res.json():
                                _logger.error(res.json())
                                self.invoice_posted = False
                                self.invoice_fiscal_documents = respost
                                return res
                        self.invoice_posted = True
            self.invoice_fiscal_documents = respost


        #self.invoice_posted = False


    def orders_get_invoice(self):
        _logger.info("orders_get_invoice")
        self.invoice_fiscal_documents = ""

    invoice_fiscal_documents = fields.Char(string='Invoice Fiscal Documents')
    invoice_posted = fields.Boolean(string='Invoice Posted')
