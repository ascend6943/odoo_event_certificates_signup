# -*- coding: utf-8 -*-
from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestReportGeneration(common.TransactionCase):
    """Check the certificate and signup sheet report data and templates."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event = cls.env['event.event'].create({
            'name': 'Fall Protection Training',
            'date_begin': '2026-10-08 14:00:00',
            'date_end': '2026-10-08 20:00:00',
            'date_tz': 'UTC',
        })
        cls.instructor = cls.env['res.partner'].create({
            'name': 'Merle L. Martin',
        })
        cls.company_acme = cls.env['res.partner'].create({
            'name': 'Acme Corp',
            'is_company': True,
        })
        cls.employee = cls.env['res.partner'].create({
            'name': 'John Doe',
            'parent_id': cls.company_acme.id,
        })
        cls.env['event.registration'].create({
            'event_id': cls.event.id,
            'partner_id': cls.employee.id,
            'name': cls.employee.name,
        })
        cls.track_1 = cls.env['event.track'].create({
            'name': 'Defining and Implementing Housekeeping',
            'event_id': cls.event.id,
            'partner_id': cls.instructor.id,
            'date': '2026-10-08 14:05:00',
            'date_end': '2026-10-08 14:45:00',
        })
        cls.track_2 = cls.env['event.track'].create({
            'name': 'Pre-employment Safety Requirements',
            'event_id': cls.event.id,
            'date': '2026-10-08 15:00:00',
            'date_end': '2026-10-08 16:00:00',
        })

    def test_certificate_values(self):
        report = self.env['report.event_certificates_signup.company_certificate_report']
        values = report._get_report_values(self.event.ids)
        docs = values['docs']
        self.assertEqual(len(docs), 1)
        doc = docs[0]
        self.assertEqual(doc['companies'], ['Acme Corp'])
        self.assertEqual(doc['topics'], sorted([
            'Defining and Implementing Housekeeping',
            'Pre-employment Safety Requirements',
        ]))
        self.assertEqual(len(doc['certificates']), 1)
        self.assertEqual(doc['certificates'][0]['company'], 'Acme Corp')
        self.assertEqual(doc['event_date'], 'October 8, 2026')

    def test_custom_certificate_template(self):
        self.event.certificate_template_html = (
            '<div class="custom">{{company}} - {{event_date}}'
            '<div>{{topics}}</div>'
            '<span>{{presented_by}}</span>{{event_name}}</div>'
        )
        report = self.env['report.event_certificates_signup.company_certificate_report']
        values = report._get_report_values(self.event.ids)
        custom_html = str(values['docs'][0]['certificates'][0]['custom_html'])
        self.assertIn('Acme Corp', custom_html)
        self.assertIn('October 8, 2026', custom_html)
        self.assertIn('<li>', custom_html)
        # Placeholders are fully replaced.
        self.assertNotIn('{{', custom_html)

    def test_signup_sheet_values(self):
        report = self.env['report.event_certificates_signup.signup_sheet_report']
        values = report._get_report_values(self.event.ids)
        sheets = values['docs'][0]['sheets']
        # One sheet per company (1) and per topic (2).
        self.assertEqual(len(sheets), 2)
        by_topic = {sheet['topic']: sheet for sheet in sheets}
        sheet = by_topic['Defining and Implementing Housekeeping']
        self.assertEqual(sheet['company'], 'Acme Corp')
        self.assertEqual(sheet['instructor_name'], 'Merle L. Martin')
        self.assertEqual(sheet['start_time'], '2:05 PM')
        self.assertEqual(sheet['finish_time'], '2:45 PM')
        # Track without an instructor must not break the report.
        sheet_2 = by_topic['Pre-employment Safety Requirements']
        self.assertFalse(sheet_2['signature'])

    def test_signup_sheet_without_company(self):
        # Remove the only company resolution path: no registration at all.
        self.event.registration_ids.unlink()
        report = self.env['report.event_certificates_signup.signup_sheet_report']
        values = report._get_report_values(self.event.ids)
        sheets = values['docs'][0]['sheets']
        self.assertEqual(len(sheets), 2)
        self.assertTrue(all(not sheet['company'] for sheet in sheets))

    def test_report_templates_render(self):
        for xmlid in (
            'event_certificates_signup.action_event_company_certificate_report',
            'event_certificates_signup.action_event_signup_sheet_report',
        ):
            html, _content_type = self.env['ir.actions.report']._render_qweb_html(
                xmlid, self.event.ids)
            self.assertIn(b'Acme Corp', html)
