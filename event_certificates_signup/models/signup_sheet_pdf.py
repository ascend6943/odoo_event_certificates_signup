# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.image import image_data_uri

from .certificate_pdf import read_background, read_layout, render_pdf_background


SIGNUP_PLACEHOLDERS = {
    'company', 'event_name', 'event_date', 'topic', 'start_time', 'finish_time',
    'instructor', 'instructor_signature', 'presented_by',
}


class EventSignupSheetPdf(models.Model):
    _inherit = 'event.event'

    signup_sheet_pdf = fields.Binary(
        string='Signup Sheet PDF', attachment=True, copy=True,
        help="Upload a single-page PDF and position fields below. One page is generated "
             "for each attending company and active topic. This takes precedence over "
             "HTML signup sheet templates. Maximum size: 20 MB.",
    )
    signup_sheet_pdf_filename = fields.Char(string='Signup Sheet PDF filename')
    signup_sheet_pdf_layout = fields.Text(string='Signup sheet field positions', copy=True)

    @api.constrains('signup_sheet_pdf')
    def _check_signup_sheet_pdf(self):
        for event in self.with_context(bin_size=False):
            if event.signup_sheet_pdf:
                read_background(event.signup_sheet_pdf)

    @api.constrains('signup_sheet_pdf_layout')
    def _check_signup_sheet_pdf_layout(self):
        for event in self:
            read_layout(event.signup_sheet_pdf_layout, SIGNUP_PLACEHOLDERS, allow_signature=True)

    def _signup_sheet_pdf_values(self, track, company):
        self.ensure_one()
        report = self.env['report.event_certificates_signup.signup_sheet_report']
        sheet = report._get_sheet_for_track(
            self, track, company, self._get_certificate_event_date(),
            self._get_certificate_presented_by(), render_custom=False,
        )
        return {
            'company': company or '', 'event_name': self.name or '',
            'event_date': sheet['event_date'], 'topic': sheet['topic'],
            'start_time': sheet['start_time'], 'finish_time': sheet['finish_time'],
            'instructor': sheet['instructor_name'] or '',
            'instructor_signature': sheet['signature'],
            'presented_by': sheet['presented_by'],
        }

    def get_signup_sheet_pdf_preview_values(self):
        """Preview the first topic/company using the same data as the printed sheet."""
        self.ensure_one()
        self.check_access('read')
        track = self._get_certificate_tracks()[:1]
        if not track:
            return {**dict.fromkeys(SIGNUP_PLACEHOLDERS, ''),
                    'event_name': self.name or '',
                    'event_date': self._get_certificate_event_date(),
                    'presented_by': self._get_certificate_presented_by()}
        company = (self._get_attendee_companies() or [''])[0]
        values = self._signup_sheet_pdf_values(track, company)
        signature = values['instructor_signature']
        values['instructor_signature'] = image_data_uri(signature) if signature else ''
        return values

    def _render_pdf_signup_sheets(self):
        self.ensure_one()
        self.check_access('read')
        event = self.with_context(bin_size=False)
        reader = read_background(event.signup_sheet_pdf)
        items = read_layout(event.signup_sheet_pdf_layout, SIGNUP_PLACEHOLDERS, allow_signature=True)
        tracks = event._get_certificate_tracks()
        if tracks and not items:
            raise UserError(_("Add at least one field to the signup sheet PDF designer, then save the event before printing."))
        companies = event._get_attendee_companies() or ['']
        rows = [event._signup_sheet_pdf_values(track, company)
                for company in companies for track in tracks]
        return render_pdf_background(reader, items, rows, _('No topics are recorded for this event.'))
