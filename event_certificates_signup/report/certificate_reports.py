# -*- coding: utf-8 -*-
from markupsafe import Markup, escape

from odoo import api, models


class CompanyCertificateReport(models.AbstractModel):
    _name = 'report.event_certificates_signup.company_certificate_report'
    _description = 'Company Certificate Report'

    @api.model
    def _render_custom_template(self, event, company, event_date, topics, presented_by):
        """Render the optional event HTML certificate template safely."""
        html = str(event.certificate_template_html or '')
        if not html:
            return False
        topics_html = Markup('<ul>%s</ul>') % Markup('').join(
            Markup('<li>%s</li>') % escape(topic) for topic in topics
        )
        replacements = {
            '{{company}}': str(escape(company or '')),
            '{{event_name}}': str(escape(event.name or '')),
            '{{event_date}}': str(escape(event_date or '')),
            '{{topics}}': str(topics_html),
            '{{presented_by}}': str(escape(presented_by or '')),
        }
        for placeholder, value in replacements.items():
            html = html.replace(placeholder, value)
        return Markup(html)

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
