# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class MatchExistingPartner(models.TransientModel):
    _name = 'match.existing.partner.wizard'
    _description = 'Match with Existing Partner'

    conversation_id = fields.Many2one('acrux.chat.conversation', 'Conversation',
                                      required=True, ondelete='cascade')
    res_partner_id = fields.Many2one('res.partner', 'Partner', ondelete='cascade')

    def match_partner(self):
        self.ensure_one()
        if not self.res_partner_id:
            raise ValidationError(_('Partner is required.'))
        self.conversation_id.res_partner_id = self.res_partner_id
        return {
            'type': 'ir.actions.act_window_close',
            'infos': {'res_partner': [self.res_partner_id.id, self.res_partner_id.name],
                      'image_url': self.conversation_id.image_url}
        }
