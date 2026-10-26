# -*- coding: utf-8 -*-
{
    'name': 'Event Certificates & Signup Sheets',
    'summary': 'Printable company certificates and topic-specific signup sheets for events',
    'version': '19.0.1.0.0',
    'category': 'Marketing/Events',
    'website': 'https://www.odoo.com/app/events',
    'description': """
Event Certificates & Signup Sheets
==================================

This module adds two printable documents for training events:

* **Company Certificate**: one certificate per company represented among the
  event attendees (deduplicated), listing the event date and the titles of the
  presented topics (event tracks). An optional HTML certificate template can be
  uploaded per event.
* **Topic Signup Sheet**: one signup sheet per company and per topic (event
  track), showing the company, event date, topic, start/finish times, instructor
  name and instructor signature image, followed by a blank attendance area.

The documents are built on the standard ``event.event``, ``event.registration``
and ``event.track`` models and do not alter the standard attendee workflow.
""",
    'depends': [
        'event',
        'website_event_track',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/report_paperformat_data.xml',
        'report/certificate_reports.xml',
        'report/signup_sheet_reports.xml',
        'wizards/certificate_wizard_view.xml',
        'wizards/signup_wizard_view.xml',
        'views/event_track_views.xml',
        'views/event_event_views.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            '/event_certificates_signup/static/src/scss/report_styles.scss',
        ],
    },
    'installable': True,
    'application': False,
    'author': 'Dawayne Safety Consulting',
    'license': 'LGPL-3',
}
