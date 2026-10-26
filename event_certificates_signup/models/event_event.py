# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import format_date


class EventEvent(models.Model):
    _inherit = 'event.event'

    certificate_template_html = fields.Html(
        string='Certificate Template (HTML)',
        sanitize_attributes=False,
        help="Optional HTML template used to render the company certificate. "
             "If left empty, the default certificate layout is used.\n"
             "Available placeholders:\n"
             "{{company}} - the attending company name\n"
             "{{event_name}} - the event name\n"
             "{{event_date}} - the event date\n"
             "{{topics}} - an HTML list of the presented topic titles\n"
             "{{presented_by}} - the name of the organizer issuing the certificate",
    )

    # ------------------------------------------------------------------
    # Report helpers (also used by the unit tests)
    # ------------------------------------------------------------------
    def _get_certificate_registrations(self):
        """Return the active registrations that represent attendance."""
        self.ensure_one()
        return self.registration_ids.filtered(
            lambda reg: reg.active and reg.state in ('open', 'done'))

    def _get_attendee_companies(self):
        """Return the deduplicated, sorted list of companies among attendees.

        Companies are deduplicated on a case-insensitive basis while keeping
        the first spelling encountered. Registrations without any resolvable
        company are silently ignored.
        """
        self.ensure_one()
        companies = {}
        for registration in self._get_certificate_registrations():
            company_name = registration._get_certificate_company_name()
            if company_name:
                companies.setdefault(company_name.casefold(), company_name)
        return sorted(companies.values(), key=lambda name: name.casefold())

    def _get_certificate_tracks(self):
        """Return the active tracks presented during the event, sorted by time."""
        self.ensure_one()
        tracks = self.track_ids.filtered('active')
        return tracks.sorted(lambda track: (track.date or fields.Datetime.now(), track.name or ''))

    def _get_certificate_topics(self):
        """Return the deduplicated, sorted list of topic titles."""
        self.ensure_one()
        topics = {}
        for track in self._get_certificate_tracks():
            title = (track.name or '').strip()
            if title:
                topics.setdefault(title.casefold(), title)
        return sorted(topics.values(), key=lambda title: title.casefold())

    def _get_certificate_event_date(self):
        """Return the event date (or date range) formatted for printing."""
        self.ensure_one()
        lang_code = self.env.context.get('lang')
        date_begin = self.date_begin
        date_end = self.date_end
        if not date_begin and not date_end:
            return ''
        if date_begin and date_end and date_begin.date() != date_end.date():
            return '%s - %s' % (
                format_date(self.env, date_begin, lang_code=lang_code, date_format='MMMM d'),
                format_date(self.env, date_end, lang_code=lang_code, date_format='MMMM d, yyyy'),
            )
        return format_date(self.env, date_begin or date_end, lang_code=lang_code,
                           date_format='MMMM d, yyyy')

    def _get_certificate_presented_by(self):
        """Return the name of the organization issuing the certificate."""
        self.ensure_one()
        return (
            (self.organizer_id.name or '').strip()
            or (self.company_id.name or '').strip()
            or self.env.company.name
            or ''
        )
