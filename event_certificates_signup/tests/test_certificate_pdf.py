# -*- coding: utf-8 -*-
import base64
import io
import json
from unittest.mock import patch

from reportlab.pdfgen import canvas

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import common, tagged
from odoo.tools.pdf import PdfReader, PdfWriter

from ..models.certificate_pdf import read_layout


@tagged('post_install', '-at_install')
class TestCertificatePdf(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.background = cls._background()
        cls.layout = {
            'version': 1,
            'fields': [{
                'id': 'company', 'template': '{{company}}',
                'x': 10, 'y': 20, 'width': 80, 'height': 12,
                'font_size': 24, 'align': 'center', 'bold': True, 'color': '#123456',
            }, {
                'id': 'details', 'template': '{{event_name}}\n{{event_date}}\n{{topics}}\n{{presented_by}}',
                'x': 10, 'y': 40, 'width': 80, 'height': 35,
                'font_size': 14, 'align': 'left', 'bold': False, 'color': '#000000',
            }],
        }
        cls.event = cls.env['event.event'].create({
            'name': 'PDF Safety Training', 'date_begin': '2026-10-08 14:00:00',
            'date_end': '2026-10-08 20:00:00', 'date_tz': 'UTC',
            'certificate_pdf': cls.background,
            'certificate_pdf_filename': 'certificate.pdf',
            'certificate_pdf_layout': json.dumps(cls.layout),
        })
        for company in ['Acme Corp', 'ACME CORP', 'Beta Excavating']:
            cls.env['event.registration'].create({
                'event_id': cls.event.id, 'name': company + ' attendee', 'company_name': company,
            })
        cls.env['event.track'].create({
            'event_id': cls.event.id, 'name': 'Fall Protection',
            'date': '2026-10-08 14:05:00', 'date_end': '2026-10-08 14:45:00',
        })

    @staticmethod
    def _background(width=792, height=612, pages=1):
        stream = io.BytesIO()
        drawing = canvas.Canvas(stream, pagesize=(width, height))
        for _page in range(pages):
            drawing.setFont('Helvetica', 18)
            drawing.drawString(40, height - 45, 'Original certificate artwork')
            drawing.showPage()
        drawing.save()
        return base64.b64encode(stream.getvalue())

    def _render(self, event=None):
        content, kind = self.env['ir.actions.report']._render_qweb_pdf(
            'event_certificates_signup.action_event_company_certificate_report',
            (event or self.event).ids,
        )
        self.assertEqual(kind, 'pdf')
        return PdfReader(io.BytesIO(content))

    def test_report_stamps_background_one_page_per_unique_company(self):
        self.event.certificate_template = '<p>HTML MUST NOT APPEAR</p>'
        pdf = self._render()
        self.assertEqual(len(pdf.pages), 2)
        for page, company in zip(pdf.pages, self.event._get_attendee_companies()):
            text = page.extract_text()
            self.assertIn('Original certificate artwork', text)
            self.assertIn(company, text)
            self.assertIn('October 8, 2026', text)
            self.assertIn('Fall Protection', text)
            self.assertNotIn('HTML MUST NOT APPEAR', text)
            self.assertNotIn('{{', text)
            self.assertEqual(float(page.mediabox.width), 792)
            self.assertEqual(float(page.mediabox.height), 612)
        self.assertNotIn('Beta Excavating', pdf.pages[0].extract_text())
        self.assertNotIn('acme corp', pdf.pages[1].extract_text().casefold())

    def test_invalid_uploads_rejected(self):
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.encrypt('password')
        encrypted = io.BytesIO()
        writer.write(encrypted)
        for value in [base64.b64encode(b'not a PDF'), self._background(pages=2),
                      base64.b64encode(encrypted.getvalue())]:
            with self.subTest(value=value[:20]), self.assertRaises(ValidationError), self.cr.savepoint():
                self.event.certificate_pdf = value

    def test_invalid_layout_rejected(self):
        for updates in [dict(x=-1), dict(y=99), dict(width=101), dict(font_size=0),
                        dict(x=float('nan')), dict(template='{{unknown}}'),
                        dict(color='not a color'), dict(align='invalid')]:
            layout = json.loads(json.dumps(self.layout))
            layout['fields'][0].update(updates)
            with self.subTest(updates=updates), self.assertRaises(ValidationError):
                read_layout(json.dumps(layout))

    def test_rotated_and_cropped_background_matches_visible_page(self):
        reader = PdfReader(io.BytesIO(base64.b64decode(self.background)))
        page = reader.pages[0]
        page.cropbox.lower_left = (50, 50)
        page.cropbox.upper_right = (750, 550)
        page.rotate(90)
        writer = PdfWriter()
        writer.add_page(page)
        output = io.BytesIO()
        writer.write(output)
        self.event.certificate_pdf = base64.b64encode(output.getvalue())
        result = self._render()
        self.assertEqual(float(result.pages[0].mediabox.width), 500)
        self.assertEqual(float(result.pages[0].mediabox.height), 700)
        self.assertEqual(result.pages[0].get('/Rotate', 0), 0)
        self.assertIn('acme corp', result.pages[0].extract_text().casefold())

    def test_no_companies_gives_information_page(self):
        self.event.registration_ids.unlink()
        pdf = self._render()
        self.assertEqual(len(pdf.pages), 1)
        self.assertIn('No company could be determined', pdf.pages[0].extract_text())

    def test_pdf_without_fields_requires_configuration(self):
        self.event.certificate_pdf_layout = False
        with self.assertRaises(UserError):
            self._render()

    def test_long_text_wraps_without_silent_truncation(self):
        company = 'A very long company name ' * 20
        registration = self.event.registration_ids[0]
        registration.company_name = company
        pdf = self._render()
        combined = '\n'.join(page.extract_text() for page in pdf.pages)
        self.assertEqual(' '.join(combined.split()).count('very long company'), 20)

    def test_field_overflow_is_actionable(self):
        self.event.registration_ids[0].company_name = 'An extremely long name ' * 100
        layout = json.loads(json.dumps(self.layout))
        layout['fields'][0].update(width=1, height=1)
        self.event.certificate_pdf_layout = json.dumps(layout)
        with self.assertRaisesRegex(UserError, 'Enlarge its box'):
            self._render()

    def test_preview_uses_existing_event_data(self):
        values = self.event.get_certificate_pdf_preview_values()
        self.assertEqual(values['company'].casefold(), 'acme corp')
        self.assertEqual(values['topics'], 'Fall Protection')
        self.assertEqual(values['event_name'], self.event.name)

    def test_unicode_company_names_are_literal_text(self):
        name = 'Müller & Söhne <Services>'
        self.event.registration_ids[0].company_name = name
        text = '\n'.join(page.extract_text() for page in self._render().pages)
        self.assertIn(name, text)

    def test_removed_pdf_uses_existing_html_path(self):
        self.event.certificate_pdf = False
        self.event.certificate_template = '<p>Old HTML {{company}}</p>'
        content, kind = self.env['ir.actions.report']._render_qweb_pdf(
            'event_certificates_signup.action_event_company_certificate_report', self.event.ids,
        )
        # Odoo deliberately renders HTML rather than launching wkhtmltopdf in tests.
        self.assertEqual(kind, 'html')
        self.assertIn(b'old html acme corp', content.lower())

    def test_pdf_report_checks_event_read_access(self):
        user = self.env['res.users'].create({
            'name': 'PDF portal test', 'login': 'event-pdf-portal-test',
            'group_ids': [(6, 0, self.env.ref('base.group_portal').ids)],
        })
        with self.assertRaises(AccessError):
            self.env['ir.actions.report'].with_user(user)._render_qweb_pdf(
                'event_certificates_signup.action_event_company_certificate_report', self.event.ids,
            )

    def test_mixed_report_uses_each_events_layout(self):
        other = self.event.copy({'certificate_pdf': False})
        # Test mixed dispatch without making HTTP requests to wkhtmltopdf.
        base = type(self.env['ir.actions.report']).__mro__
        from ..models.ir_actions_report import CertificateActionsReport
        index = next(i for i, cls in enumerate(base) if cls is CertificateActionsReport)
        parent = next(cls for cls in base[index + 1:] if '_render_qweb_pdf' in cls.__dict__)
        blank = base64.b64decode(self._background(width=612, height=792))
        with patch.object(parent, '_render_qweb_pdf', return_value=(blank, 'pdf')) as fallback:
            content, kind = self.env['ir.actions.report']._render_qweb_pdf(
                'event_certificates_signup.action_event_company_certificate_report', (self.event | other).ids,
            )
        self.assertEqual(kind, 'pdf')
        self.assertEqual(len(PdfReader(io.BytesIO(content)).pages), 3)
        fallback.assert_called_once()
