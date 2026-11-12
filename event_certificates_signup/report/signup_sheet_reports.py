# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.tools import format_time
from odoo.tools.image import image_data_uri

from . import template_utils


class SignupSheetReport(models.AbstractModel):
    _name = 'report.event_certificates_signup.signup_sheet_report'
    _description = 'Topic Signup Sheet Report'

    @api.model
    def _get_time_str(self, event, value):
        if not value:
            return ''
        return format_time(
            self.env, value,
            tz=event.date_tz or self.env.user.tz,
            lang_code=self.env.context.get('lang'),
            time_format='h:mm a',
        )

    @api.model
    def _get_raw_custom_template(self, event):
        """Return the configured template source, preferring the plain text field.

        ``signup_sheet_template`` is a plain ``Text`` field: it stores HTML/CSS
        verbatim. ``signup_sheet_template_html`` is a sanitized ``Html`` field
        kept for backwards compatibility; because the sanitizer escapes pasted
        source it is only used as a fallback and gets extra cleanup.
        """
        plain = (event.signup_sheet_template or '').strip()
        if plain:
            return plain, False
        legacy = str(event.signup_sheet_template_html or '').strip()
        if legacy:
            return legacy, True
        return '', False

    @api.model
    def _restore_legacy_source(self, raw_html):
        """Backwards-compatible wrapper around the shared helper."""
        return template_utils.restore_legacy_source(raw_html)

    @api.model
    def _normalize_custom_html(self, raw_html, legacy=False):
        """Backwards-compatible wrapper around the shared helper."""
        return template_utils.normalize_template(raw_html, legacy=legacy)

    @api.model
    def _render_sheet_template(self, event, sheet):
        """Render the optional event HTML signup sheet template safely."""
        raw, legacy = self._get_raw_custom_template(event)
        template = self._normalize_custom_html(raw, legacy=legacy)
        if not template:
            return False
        signature_uri = ''
        if sheet['signature']:
            signature_uri = image_data_uri(sheet['signature'])
        replacements = {
            'company': sheet['company'] or '',
            'event_name': event.name or '',
            'event_date': sheet['event_date'] or '',
            'topic': sheet['topic'] or '',
            'start_time': sheet['start_time'] or '',
            'finish_time': sheet['finish_time'] or '',
            'instructor': sheet['instructor_name'] or '',
            # Attribute-only value: expanded to a data URI inside an attribute
            # such as ``<img src="{{instructor_signature}}"/>`` and emptied when
            # used as plain text (a raw data URI would print as base64 text).
            'instructor_signature': template_utils.ResourceValue(signature_uri),
            'presented_by': sheet['presented_by'] or '',
        }
        return template_utils.render_template(template, replacements)

    @api.model
    def _get_sheet_for_track(self, event, track, company, event_date, presented_by, render_custom=True):
        sheet = {
            'company': company,
            'track': track,
            'topic': track.name or '',
            'instructor_name': track._get_instructor_name(),
            'signature': track._get_instructor_signature(),
            'start_time': self._get_time_str(event, track.date or event.date_begin),
            'finish_time': self._get_time_str(event, track.date_end or event.date_end),
            'event_date': event_date,
            'presented_by': presented_by,
        }
        sheet['custom_html'] = self._render_sheet_template(event, sheet) if render_custom else False
        return sheet

    @api.model
    def _get_report_values(self, docids, data=None):
        events = self.env['event.event'].browse(docids)
        docs = []
        for event in events:
            event = event.with_context(tz=event.date_tz or self.env.user.tz)
            event_date = event._get_certificate_event_date()
            presented_by = event._get_certificate_presented_by()
            companies = event._get_attendee_companies()
            tracks = event._get_certificate_tracks()

            # One sheet per (company, topic). When no company can be resolved
            # among the attendees, one sheet per topic is generated with a blank
            # company so that the information is not lost.
            sheet_companies = companies or ['']
            sheets = [
                self._get_sheet_for_track(event, track, company, event_date, presented_by)
                for company in sheet_companies
                for track in tracks
            ]

            docs.append({
                'event': event,
                'event_date': event_date,
                'presented_by': presented_by,
                'companies': companies,
                'sheets': sheets,
            })

        return {
            'doc_ids': events.ids,
            'doc_model': 'event.event',
            'docs': docs,
        }
