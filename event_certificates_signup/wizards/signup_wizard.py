# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EventSignupSheetWizard(models.TransientModel):
    _name = 'event.signup.sheet.wizard'
    _description = 'Generate Signup Sheets'

    event_id = fields.Many2one(
        'event.event', string='Event', required=True,
        help="Event for which the signup sheets are generated.")
    event_ids = fields.Many2many('event.event', string='Events')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'event.event' and self.env.context.get('active_ids'):
            active_ids = self.env.context['active_ids']
            res['event_ids'] = [(6, 0, active_ids)]
            if len(active_ids) == 1:
                res['event_id'] = active_ids[0]
        return res

    def action_print_signup_sheets(self):
        self.ensure_one()
        events = self.event_ids or self.event_id
        if not events:
            raise UserError(_("Please select at least one event."))
        return self.env.ref(
            'event_certificates_signup.action_event_signup_sheet_report'
        ).report_action(events)
