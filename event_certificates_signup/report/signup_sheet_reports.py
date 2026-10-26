# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.tools import format_time


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
    def _get_sheet_for_track(self, event, track, company, event_date, presented_by):
        return {
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
