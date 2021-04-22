from odoo import fields, models, api
from odoo.exceptions import ValidationError
from datetime import datetime

class MeliPayment(models.Model):
    _inherit = 'mercadolibre.payments'

    def _get_ml_journal(self):
        journal_id = self.env.user.company_id.mercadolibre_process_payments_journal
        if not journal_id:
            journal_id = self.env['account.journal'].search([('code','=','ML')])
        if not journal_id:
            journal_id = self.env['account.journal'].search([('code','=','MP')])
        return journal_id

    def _get_ml_partner(self):
        partner_id = self.env.user.company_id.mercadolibre_process_payments_res_partner
        if not partner_id:
            partner_id = self.env['res.partner'].search([('ref','=','MELI')])
        if not partner_id:
            partner_id = self.env['res.partner'].search([('name','=','MercadoLibre')])
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
        payment_method_id = self.env['account.payment.method'].search([('code','=','electronic'),('payment_type','=','inbound')], limit=1)
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
        payment_method_id = self.env['account.payment.method'].search([('code','=','outbound_online'),('payment_type','=','outbound')], limit=1)
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
        payment_method_id = self.env['account.payment.method'].search([('code','=','outbound_online'),('payment_type','=','outbound')], limit=1)
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

    account_payment_id = fields.Many2one('account.payment',string='Pago')
    account_supplier_payment_id = fields.Many2one('account.payment',string='Pago a Proveedor')
    account_supplier_payment_shipment_id = fields.Many2one('account.payment',string='Pago Envio a Proveedor')


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    meli_payment_id = fields.Many2one('mercadolibre.payments',string='Pago de MP')
