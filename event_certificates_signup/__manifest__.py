# -*- coding: utf-8 -*-
{
    'name': 'Event Certificates & Signup Sheets',
    'summary': 'Printable company certificates and topic-specific signup sheets for events',
    'version': '19.0.1.2.0',
    'category': 'Marketing/Events',
    'website': 'https://github.com/ascend6943/odoo_event_certificates_signup',
    'description': """
Event Certificates & Signup Sheets
==================================

This module adds two printable documents for training events:

* **Company Certificate**: one certificate per company represented among the
  event attendees (deduplicated), listing the event date and the titles of the
  presented topics (event tracks). Upload a PDF certificate background and drag
  data fields into position, or use the existing HTML template fallback.
* **Topic Signup Sheet**: one signup sheet per company and per topic (event
  track), showing the company, event date, topic, start/finish times, instructor
  name and instructor signature image, followed by a blank attendance area.
  Upload a PDF signup sheet and position text/signature fields on it.

The documents are built on the standard ``event.event``, ``event.registration``
and ``event.track`` models and do not alter the standard attendee workflow.
""",
    'depends': [
        'event',
        'website_event_track',
    ],
    'external_dependencies': {'python': ['PyPDF2', 'reportlab']},
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
        'web.assets_backend': [
            'event_certificates_signup/static/src/js/certificate_pdf_designer.js',
            'event_certificates_signup/static/src/xml/certificate_pdf_designer.xml',
            'event_certificates_signup/static/src/scss/certificate_pdf_designer.scss',
        ],
        'web.report_assets_common': [
            '/event_certificates_signup/static/src/scss/report_styles.scss',
        ],
    },
    'installable': True,
    'application': False,
    'author': 'Community Contributors',
    'license': 'LGPL-3',
}
