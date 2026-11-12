# -*- coding: utf-8 -*-
from markupsafe import Markup, escape

from odoo import api, models

from . import template_utils


class CompanyCertificateReport(models.AbstractModel):
    _name = 'report.event_certificates_signup.company_certificate_report'
    _description = 'Company Certificate Report'

    @api.model
    def _get_raw_custom_template(self, event):
        """Return the configured template source, preferring the plain text field.

        ``certificate_template`` is a plain ``Text`` field: it stores HTML/CSS
        verbatim. ``certificate_template_html`` is a sanitized ``Html`` field
        kept for backwards compatibility; because the sanitizer escapes pasted
        source it is only used as a fallback and gets extra cleanup.
        """
        plain = (event.certificate_template or '').strip()
        if plain:
            return plain, False
        legacy = str(event.certificate_template_html or '').strip()
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
    def _render_custom_template(self, event, company, event_date, topics, presented_by):
        """Render the optional event HTML certificate template safely."""
        raw, legacy = self._get_raw_custom_template(event)
        template = self._normalize_custom_html(raw, legacy=legacy)
        if not template:
            return False
        topics_html = Markup('<ul>%s</ul>') % Markup('').join(
            Markup('<li>%s</li>') % escape(topic) for topic in topics
        )
        replacements = {
            'company': company or '',
            'event_name': event.name or '',
            'event_date': event_date or '',
            'topics': topics_html,
            'presented_by': presented_by or '',
        }
        return template_utils.render_template(template, replacements)

    @api.model
    def _get_report_values(self, docids, data=None):
        events = self.env['event.event'].browse(docids)
        docs = []
        for event in events:
            event = event.with_context(tz=event.date_tz or self.env.user.tz)
            event_date = event._get_certificate_event_date()
            presented_by = event._get_certificate_presented_by()
            topics = event._get_certificate_topics()
            companies = event._get_attendee_companies()

            certificates = [{
                'company': company,
                'custom_html': self._render_custom_template(
                    event, company, event_date, topics, presented_by),
            } for company in companies]

            docs.append({
                'event': event,
                'event_date': event_date,
                'presented_by': presented_by,
                'topics': topics,
                'companies': companies,
                'certificates': certificates,
            })

        return {
            'doc_ids': events.ids,
            'doc_model': 'event.event',
            'docs': docs,
        }
