# -*- coding: utf-8 -*-
import base64
import io
import json
from unittest.mock import patch

from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import common, tagged
from odoo.tools.pdf import PdfReader, PdfWriter

from ..models.certificate_pdf import read_layout
from ..models.signup_sheet_pdf import SIGNUP_PLACEHOLDERS


@tagged('post_install', '-at_install')
class TestSignupSheetPdf(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        background = io.BytesIO()
        drawing = canvas.Canvas(background, pagesize=(612, 792))
        drawing.drawString(40, 750, 'Original signup sheet artwork')
        drawing.save()
        cls.background = base64.b64encode(background.getvalue())
        cls.layout = {'version': 1, 'fields': [{
            'id': 'company', 'template': '{{company}}', 'kind': 'text',
            'x': 10, 'y': 10, 'width': 80, 'height': 8,
            'font_size': 22, 'align': 'center', 'bold': True, 'color': '#123456',
        }, {
            'id': 'details', 'kind': 'text',
            'template': '{{event_name}}\n{{event_date}}\n{{topic}}\n{{start_time}} - {{finish_time}}\nInstructor: {{instructor}}\n{{presented_by}}',
            'x': 10, 'y': 22, 'width': 80, 'height': 35,
            'font_size': 14, 'align': 'left', 'bold': False, 'color': '#000000',
        }, {
            'id': 'signature', 'template': '{{instructor_signature}}', 'kind': 'image',
            'x': 10, 'y': 75, 'width': 30, 'height': 10,
            'font_size': 14, 'align': 'center', 'bold': False, 'color': '#000000',
        }]}
        cls.event = cls.env['event.event'].create({
            'name': 'PDF Signup Safety Training', 'date_begin': '2026-10-08 14:00:00',
            'date_end': '2026-10-08 20:00:00', 'date_tz': 'America/New_York',
            'signup_sheet_pdf': cls.background, 'signup_sheet_pdf_filename': 'signup.pdf',
            'signup_sheet_pdf_layout': json.dumps(cls.layout),
        })
        for company in ['Acme Corp', 'ACME CORP', 'Beta Excavating']:
            cls.env['event.registration'].create({
                'event_id': cls.event.id, 'name': company + ' attendee', 'company_name': company,
            })
        image = Image.new('RGBA', (300, 80), (0, 0, 0, 0))
        ImageDraw.Draw(image).line([(10, 60), (60, 10), (90, 65), (200, 25), (280, 50)], fill='black', width=3)
        signature = io.BytesIO()
        image.save(signature, format='PNG')
        cls.signature = base64.b64encode(signature.getvalue())
        cls.instructor = cls.env['res.partner'].create({
            'name': 'Signup Instructor', 'instructor_signature': cls.signature,
        })
        cls.track_1 = cls.env['event.track'].create({
            'event_id': cls.event.id, 'name': 'Fall Protection', 'partner_id': cls.instructor.id,
            'date': '2026-10-08 14:05:00', 'date_end': '2026-10-08 14:45:00',
        })
        cls.track_2 = cls.env['event.track'].create({
            'event_id': cls.event.id, 'name': 'Housekeeping', 'user_id': False,
            'date': '2026-10-08 15:00:00', 'date_end': '2026-10-08 15:30:00',
        })

    def _render(self, events=None):
        content, kind = self.env['ir.actions.report']._render_qweb_pdf(
            'event_certificates_signup.action_event_signup_sheet_report', (events or self.event).ids,
        )
        self.assertEqual(kind, 'pdf')
        return PdfReader(io.BytesIO(content))

    @staticmethod
    def _images(page):
        objects = page['/Resources'].get('/XObject', {})
        return [value.get_object() for value in objects.values()
                if value.get_object().get('/Subtype') == '/Image']

    def test_company_topic_cross_product_and_correct_values(self):
        self.event.signup_sheet_template = '<p>HTML MUST NOT APPEAR</p>'
        pdf = self._render()
        self.assertEqual(len(pdf.pages), 4)
        expected = [(company, track) for company in self.event._get_attendee_companies()
                    for track in self.event._get_certificate_tracks()]
        for page, (company, track) in zip(pdf.pages, expected):
            text = page.extract_text()
            self.assertIn(company, text)
            self.assertIn(track.name, text)
            self.assertNotIn((self.track_2 if track == self.track_1 else self.track_1).name, text)
            self.assertIn('Original signup sheet artwork', text)
            self.assertIn('October 8, 2026', text)
            self.assertNotIn('{{', text)
            self.assertNotIn('data:image', text)
            self.assertNotIn('HTML MUST NOT APPEAR', text)
            self.assertEqual((float(page.mediabox.width), float(page.mediabox.height)), (612, 792))
        self.assertIn('10:05 AM - 10:45 AM', pdf.pages[0].extract_text())
        self.assertIn('11:00 AM - 11:30 AM', pdf.pages[1].extract_text())

    def test_signature_is_transparent_image_with_contact_fallback(self):
        pdf = self._render()
        self.assertTrue(self._images(pdf.pages[0]))
        self.assertIn('/SMask', self._images(pdf.pages[0])[0])
        self.assertFalse(self._images(pdf.pages[1]))
        self.assertIn('Signup Instructor', pdf.pages[0].extract_text())
        self.assertNotIn('Signup Instructor', pdf.pages[1].extract_text())

    def test_track_signature_overrides_contact(self):
        self.track_2.instructor_signature = self.signature
        self.assertTrue(self._images(self._render().pages[1]))

    def test_no_companies_still_prints_each_topic(self):
        self.event.registration_ids.unlink()
        pdf = self._render()
        self.assertEqual(len(pdf.pages), 2)
        self.assertIn('Fall Protection', pdf.pages[0].extract_text())
        self.assertIn('Housekeeping', pdf.pages[1].extract_text())
        self.assertNotIn('Acme', '\n'.join(page.extract_text() for page in pdf.pages))

    def test_no_topics_prints_information(self):
        self.event.track_ids.active = False
        pdf = self._render()
        self.assertEqual(len(pdf.pages), 1)
        self.assertIn('No topics are recorded', pdf.pages[0].extract_text())

    def test_inactive_topics_and_cancelled_registrations_ignored(self):
        self.track_2.active = False
        self.event.registration_ids.filtered(lambda r: r.company_name.casefold() == 'acme corp').state = 'cancel'
        pdf = self._render()
        self.assertEqual(len(pdf.pages), 1)
        self.assertIn('Beta Excavating', pdf.pages[0].extract_text())
        self.assertIn('Fall Protection', pdf.pages[0].extract_text())

    def test_preview_matches_printed_values_and_signature(self):
        values = self.event.get_signup_sheet_pdf_preview_values()
        self.assertEqual(values['company'].casefold(), 'acme corp')
        self.assertEqual(values['topic'], 'Fall Protection')
        self.assertEqual(values['start_time'], '10:05 AM')
        self.assertEqual(values['finish_time'], '10:45 AM')
        self.assertEqual(values['instructor'], 'Signup Instructor')
        self.assertTrue(values['instructor_signature'].startswith('data:image/png;base64,'))

    def test_empty_preview_is_safe(self):
        self.event.track_ids.active = False
        values = self.event.get_signup_sheet_pdf_preview_values()
        self.assertEqual(values['topic'], '')
        self.assertEqual(values['instructor_signature'], '')

    def test_invalid_pdf_and_layout_are_rejected(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.event.signup_sheet_pdf = base64.b64encode(b'not a PDF')
        layout = json.loads(json.dumps(self.layout))
        layout['fields'][0]['x'] = -1
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.event.signup_sheet_pdf_layout = json.dumps(layout)
        for changes in [dict(kind='text'), dict(template='{{company}}'), dict(kind='remote-image')]:
            layout = json.loads(json.dumps(self.layout))
            layout['fields'][2].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                read_layout(json.dumps(layout), SIGNUP_PLACEHOLDERS, allow_signature=True)

    def test_no_fields_requires_configuration(self):
        self.event.signup_sheet_pdf_layout = False
        with self.assertRaises(UserError):
            self._render()

    def test_pdf_path_does_not_render_html(self):
        report = self.env['report.event_certificates_signup.signup_sheet_report']
        with patch.object(type(report), '_render_sheet_template', side_effect=AssertionError('Should not render HTML')):
            self.assertEqual(len(self._render().pages), 4)

    def test_removed_pdf_uses_previous_html(self):
        self.event.signup_sheet_pdf = False
        self.event.signup_sheet_template = '<p>Old signup HTML {{company}} {{topic}}</p>'
        content, kind = self.env['ir.actions.report']._render_qweb_pdf(
            'event_certificates_signup.action_event_signup_sheet_report', self.event.ids,
        )
        self.assertEqual(kind, 'html')
        self.assertIn(b'old signup html acme corp fall protection', content.lower())

    def test_report_and_preview_respect_read_access(self):
        user = self.env['res.users'].create({
            'name': 'Signup PDF portal', 'login': 'signup-pdf-portal-test',
            'group_ids': [(6, 0, self.env.ref('base.group_portal').ids)],
        })
        with self.assertRaises(AccessError):
            self.event.with_user(user).get_signup_sheet_pdf_preview_values()
        with self.assertRaises(AccessError):
            self.env['ir.actions.report'].with_user(user)._render_qweb_pdf(
                'event_certificates_signup.action_event_signup_sheet_report', self.event.ids,
            )

    def test_rotated_cropped_signup_background(self):
        reader = PdfReader(io.BytesIO(base64.b64decode(self.background)))
        page = reader.pages[0]
        page.cropbox.lower_left = (20, 20)
        page.cropbox.upper_right = (590, 770)
        page.rotate(90)
        writer = PdfWriter()
        writer.add_page(page)
        stream = io.BytesIO()
        writer.write(stream)
        self.event.signup_sheet_pdf = base64.b64encode(stream.getvalue())
        pdf = self._render()
        self.assertEqual(len(pdf.pages), 4)
        self.assertEqual((float(pdf.pages[0].mediabox.width), float(pdf.pages[0].mediabox.height)), (750, 570))
        self.assertTrue(self._images(pdf.pages[0]))

    def test_mixed_signup_pdf_and_html_events(self):
        other = self.event.copy({'signup_sheet_pdf': False})
        from ..models.ir_actions_report import CertificateActionsReport
        classes = type(self.env['ir.actions.report']).__mro__
        index = classes.index(CertificateActionsReport)
        parent = next(cls for cls in classes[index + 1:] if '_render_qweb_pdf' in cls.__dict__)
        with patch.object(parent, '_render_qweb_pdf', return_value=(base64.b64decode(self.background), 'pdf')) as fallback:
            self.assertEqual(len(self._render(self.event | other).pages), 5)
        fallback.assert_called_once()
