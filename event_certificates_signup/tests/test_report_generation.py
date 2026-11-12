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
            'name': 'Test Instructor',
        })
        cls.company_a = cls.env['res.partner'].create({
            'name': 'Company A',
            'is_company': True,
        })
        cls.employee = cls.env['res.partner'].create({
            'name': 'John Doe',
            'parent_id': cls.company_a.id,
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
        # 1x1 transparent PNG used as the instructor signature.
        cls.signature_png = (
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk'
            'YAAAAAYAAjCB0C8AAAAASUVORK5CYII='
        )
        cls.track_1.instructor_signature = cls.signature_png

    def test_certificate_values(self):
        report = self.env['report.event_certificates_signup.company_certificate_report']
        values = report._get_report_values(self.event.ids)
        docs = values['docs']
        self.assertEqual(len(docs), 1)
        doc = docs[0]
        self.assertEqual(doc['companies'], ['Company A'])
        self.assertEqual(doc['topics'], sorted([
            'Defining and Implementing Housekeeping',
            'Pre-employment Safety Requirements',
        ]))
        self.assertEqual(len(doc['certificates']), 1)
        self.assertEqual(doc['certificates'][0]['company'], 'Company A')
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
        self.assertIn('Company A', custom_html)
        self.assertIn('October 8, 2026', custom_html)
        self.assertIn('<li>', custom_html)
        # Placeholders are fully replaced.
        self.assertNotIn('{{', custom_html)

    def test_custom_certificate_plain_text_field(self):
        # The plain Text field stores the template verbatim, including a full
        # HTML document and its <style> block.
        self.event.certificate_template = (
            '<!DOCTYPE html>\n'
            '<html lang="en">\n<head>\n'
            '<style>.certificate-title { color: #e76f51; }</style>\n'
            '</head>\n<body>\n'
            '<div class="certificate">\n'
            '<div class="certificate-title">Safety Training</div>\n'
            '<div><strong>{{company}}</strong></div>\n'
            '<div>{{topics}}</div>\n'
            '</div>\n</body>\n</html>'
        )
        report = self.env['report.event_certificates_signup.company_certificate_report']
        normalized = report._normalize_custom_html(self.event.certificate_template)
        self.assertNotIn('<!DOCTYPE', normalized)
        self.assertIn('<style>', normalized)
        self.assertIn('Safety Training', normalized)
        self.assertIn('.certificate-title', normalized)

        values = report._get_report_values(self.event.ids)
        custom_html = str(values['docs'][0]['certificates'][0]['custom_html'])
        self.assertIn('Company A', custom_html)
        self.assertIn('certificate-title', custom_html)
        self.assertIn('<li>', custom_html)
        self.assertNotIn('{{', custom_html)
        self.assertNotIn('<!DOCTYPE', custom_html)

    def test_custom_certificate_plain_text_preferred(self):
        # When both fields are set, the plain Text field wins.
        self.event.certificate_template = '<div>PLAIN {{company}}</div>'
        self.event.certificate_template_html = '<div>LEGACY {{company}}</div>'
        report = self.env['report.event_certificates_signup.company_certificate_report']
        values = report._get_report_values(self.event.ids)
        custom_html = str(values['docs'][0]['certificates'][0]['custom_html'])
        self.assertIn('PLAIN', custom_html)
        self.assertNotIn('LEGACY', custom_html)

    def test_legacy_rich_text_full_document(self):
        # A complete HTML document pasted into the sanitized Html field is
        # stored with escaped brackets, per-line <div> wrappers and &nbsp;
        # indentation. The report must still recover and render it.
        source = (
            '<!DOCTYPE html>\n'
            '<html lang="en">\n<head>\n'
            '<style>.certificate-title { color: #e76f51; }</style>\n'
            '</head>\n<body>\n'
            '<div class="certificate">\n'
            '<div class="certificate-title">Safety Training</div>\n'
            '<div><strong>{{company}}</strong></div>\n'
            '<div>{{topics}}</div>\n'
            '</div>\n</body>\n</html>'
        )
        import html as html_lib
        escaped = html_lib.escape(source)
        # Mimic the sanitizer: per-line <div> wrappers, indentation as &nbsp;.
        lines = []
        for line in escaped.split('\n'):
            indent = len(line) - len(line.lstrip(' '))
            line = '&nbsp;' * indent + line.lstrip(' ')
            lines.append('<div>%s</div>' % line)
        stored = '<div data-oe-version="2.0">%s</div>' % ''.join(lines)
        self.event.certificate_template = False
        self.event.certificate_template_html = stored

        report = self.env['report.event_certificates_signup.company_certificate_report']
        normalized = report._normalize_custom_html(stored, legacy=True)
        self.assertNotIn('&lt;', normalized)
        self.assertNotIn('<!DOCTYPE', normalized)
        self.assertIn('<style>', normalized)
        self.assertIn('Safety Training', normalized)
        # Indentation must not survive as non-breaking spaces.
        self.assertNotIn('\xa0', normalized)

        values = report._get_report_values(self.event.ids)
        custom_html = str(values['docs'][0]['certificates'][0]['custom_html'])
        self.assertIn('Company A', custom_html)
        self.assertIn('<li>', custom_html)
        self.assertNotIn('{{', custom_html)
        self.assertNotIn('&lt;!DOCTYPE', custom_html)
        self.assertNotIn('\xa0', custom_html)

    def test_signup_sheet_values(self):
        report = self.env['report.event_certificates_signup.signup_sheet_report']
        values = report._get_report_values(self.event.ids)
        sheets = values['docs'][0]['sheets']
        # One sheet per company (1) and per topic (2).
        self.assertEqual(len(sheets), 2)
        by_topic = {sheet['topic']: sheet for sheet in sheets}
        sheet = by_topic['Defining and Implementing Housekeeping']
        self.assertEqual(sheet['company'], 'Company A')
        self.assertEqual(sheet['instructor_name'], 'Test Instructor')
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

    def test_signup_sheet_plain_text_template(self):
        # The plain Text field stores a full HTML document verbatim.
        self.event.signup_sheet_template = (
            '<!DOCTYPE html>\n'
            '<html lang="en">\n<head>\n'
            '<style>.sheet-title { color: #2d6cdf; }</style>\n'
            '</head>\n<body>\n'
            '<div class="sheet">\n'
            '<div class="sheet-title">{{topic}}</div>\n'
            '<div>{{company}}</div>\n'
            '<div>{{start_time}} - {{finish_time}}</div>\n'
            '<div>{{instructor}}</div>\n'
            '<div>{{event_date}}</div>\n'
            '<div>{{presented_by}}</div>\n'
            '</div>\n</body>\n</html>'
        )
        report = self.env['report.event_certificates_signup.signup_sheet_report']
        values = report._get_report_values(self.event.ids)
        sheets = values['docs'][0]['sheets']
        self.assertEqual(len(sheets), 2)
        by_topic = {sheet['topic']: sheet for sheet in sheets}
        sheet = by_topic['Defining and Implementing Housekeeping']

        custom_html = str(sheet['custom_html'])
        self.assertIn('sheet-title', custom_html)
        self.assertIn('<style>', custom_html)
        self.assertNotIn('<!DOCTYPE', custom_html)
        self.assertNotIn('{{', custom_html)
        self.assertIn('Defining and Implementing Housekeeping', custom_html)
        self.assertIn('Company A', custom_html)
        self.assertIn('2:05 PM', custom_html)
        self.assertIn('2:45 PM', custom_html)
        self.assertIn('Test Instructor', custom_html)
        self.assertIn('October 8, 2026', custom_html)

    def test_signup_sheet_template_placeholder_signature(self):
        # Inside an <img src> the placeholder expands to a data URI when a
        # signature exists, and to an empty value when it does not.
        self.event.signup_sheet_template = (
            '<img src="{{instructor_signature}}" class="sig"/>'
            '<span>{{topic}}</span>'
        )
        report = self.env['report.event_certificates_signup.signup_sheet_report']
        values = report._get_report_values(self.event.ids)
        sheets = values['docs'][0]['sheets']
        by_topic = {sheet['topic']: sheet for sheet in sheets}
        self.assertNotIn('{{', str(sheets[0]['custom_html']))

        # Track with a signature image: a real data URI is produced.
        with_sig = by_topic['Defining and Implementing Housekeeping']
        self.assertIn('data:image/png;base64,', str(with_sig['custom_html']))

        # Track without an instructor/signature: empty src, no base64 text.
        without_sig = by_topic['Pre-employment Safety Requirements']
        self.assertIn('src=""', str(without_sig['custom_html']))
        self.assertNotIn('data:image', str(without_sig['custom_html']))

    def test_signup_sheet_template_bare_signature_no_base64_dump(self):
        # When the author forgets to put the signature in an <img src>, the
        # placeholder must not dump a wall of base64 into the page text.
        self.event.signup_sheet_template = (
            '<div>{{topic}}</div><div>{{instructor_signature}}</div>'
        )
        report = self.env['report.event_certificates_signup.signup_sheet_report']
        values = report._get_report_values(self.event.ids)
        sheet = [s for s in values['docs'][0]['sheets']
                 if s['topic'] == 'Defining and Implementing Housekeeping'][0]
        custom_html = str(sheet['custom_html'])
        self.assertNotIn('data:image', custom_html)
        self.assertNotIn('{{', custom_html)

    def test_signup_sheet_template_nbsp_cleanup(self):
        # Word/Outlook HTML is full of &nbsp;; it must not surface as a stray
        # non-breaking space (rendered as a visible 'Â' by some renderers).
        self.event.signup_sheet_template = (
            '<div>&nbsp;{{topic}}&nbsp;</div><div>&#160;{{company}}</div>'
        )
        report = self.env['report.event_certificates_signup.signup_sheet_report']
        values = report._get_report_values(self.event.ids)
        sheet = values['docs'][0]['sheets'][0]
        custom_html = str(sheet['custom_html'])
        self.assertNotIn('&nbsp;', custom_html)
        self.assertNotIn('\xa0', custom_html)
        self.assertNotIn('\u00c2', custom_html)

    def test_signup_sheet_plain_text_preferred(self):
        # When both fields are set, the plain Text field wins.
        self.event.signup_sheet_template = '<div>PLAIN {{topic}}</div>'
        self.event.signup_sheet_template_html = '<div>LEGACY {{topic}}</div>'
        report = self.env['report.event_certificates_signup.signup_sheet_report']
        values = report._get_report_values(self.event.ids)
        sheet = values['docs'][0]['sheets'][0]
        custom_html = str(sheet['custom_html'])
        self.assertIn('PLAIN', custom_html)
        self.assertNotIn('LEGACY', custom_html)

    def test_signup_sheet_legacy_rich_text_template(self):
        # A legacy sanitized value must be recovered and rendered.
        import html as html_lib
        source = (
            '<div class="sheet">{{topic}}<div>{{company}}</div></div>'
        )
        escaped = html_lib.escape(source)
        stored = '<div data-oe-version="2.0">%s</div>' % escaped.replace(
            '\n', '</div><div>')
        self.event.signup_sheet_template = False
        self.event.signup_sheet_template_html = stored
        report = self.env['report.event_certificates_signup.signup_sheet_report']
        values = report._get_report_values(self.event.ids)
        sheet = values['docs'][0]['sheets'][0]
        custom_html = str(sheet['custom_html'])
        self.assertIn('sheet', custom_html)
        self.assertIn('Company A', custom_html)
        self.assertIn('Defining and Implementing Housekeeping', custom_html)
        self.assertNotIn('{{', custom_html)

    def test_custom_signup_sheet_renders(self):
        # End-to-end: a custom template must be injected into the report HTML.
        self.event.signup_sheet_template = (
            '<div class="my-sheet-marker">{{company}} / {{topic}}</div>'
        )
        html, _content_type = self.env['ir.actions.report']._render_qweb_html(
            'event_certificates_signup.action_event_signup_sheet_report',
            self.event.ids)
        self.assertIn(b'my-sheet-marker', html)

    def test_report_templates_render(self):
        for xmlid in (
            'event_certificates_signup.action_event_company_certificate_report',
            'event_certificates_signup.action_event_signup_sheet_report',
        ):
            html, _content_type = self.env['ir.actions.report']._render_qweb_html(
                xmlid, self.event.ids)
            self.assertIn(b'Company A', html)
