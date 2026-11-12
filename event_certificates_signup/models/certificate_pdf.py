# -*- coding: utf-8 -*-
"""PDF backgrounds and positioned, data-driven certificate text."""
import base64
import copy
import io
import json
import math
import re

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import file_open
from odoo.tools.pdf import PdfReader, PdfWriter
from odoo.tools.translate import LazyTranslate


PLACEHOLDERS = {'company', 'event_name', 'event_date', 'topics', 'presented_by'}
PLACEHOLDER_RE = re.compile(r'\{\{\s*(\w+)\s*\}\}')
MAX_PDF_BYTES = 20 * 1024 * 1024
_lt = LazyTranslate(__name__)


def read_background(value):
    """Validate a single-page PDF, including encrypted and malformed uploads."""
    try:
        raw = base64.b64decode(value, validate=True)
        if len(raw) > MAX_PDF_BYTES:
            raise ValidationError(_lt("The template PDF must be smaller than 20 MB."))
        if not raw.lstrip().startswith(b'%PDF-'):
            raise ValueError('Not a PDF')
        reader = PdfReader(io.BytesIO(raw), strict=False)
        if reader.is_encrypted:
            raise ValidationError(_lt("Please upload a PDF without password protection."))
        if len(reader.pages) != 1:
            raise ValidationError(_lt("Upload a single-page PDF background."))
        page = reader.pages[0]
        box = page.cropbox
        dimensions = [float(box.width), float(box.height)]
        if not all(math.isfinite(v) and 10 <= v <= 14400 for v in dimensions):
            raise ValueError('Invalid page dimensions')
        # Force content parsing now, rather than failing after accepting an upload.
        page.get_contents()
        return reader
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError(_lt("This file could not be read as a PDF template. Please export it again.")) from exc


def read_layout(value, placeholders=None, allow_signature=False):
    """Treat layout data from the browser as untrusted; coordinates are percentages."""
    if not value:
        return []
    placeholders = PLACEHOLDERS if placeholders is None else placeholders
    try:
        layout = json.loads(value)
        if not isinstance(layout, dict) or layout.get('version') != 1:
            raise ValueError('Unsupported layout')
        items = layout.get('fields')
        if not isinstance(items, list) or len(items) > 100:
            raise ValueError('Invalid field list')
        identifiers = set()
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Invalid field')
            identifier = item.get('id')
            if not isinstance(identifier, str) or not identifier or identifier in identifiers:
                raise ValueError('Invalid field identifier')
            identifiers.add(identifier)
            text = item.get('template')
            if not isinstance(text, str) or not text.strip() or len(text) > 4000:
                raise ValueError('Invalid field text')
            names = set(PLACEHOLDER_RE.findall(text))
            if names - placeholders:
                raise ValueError('Unknown placeholder')
            kind = item.get('kind', 'text')
            if kind not in ('text', 'image'):
                raise ValueError('Invalid field type')
            if kind == 'image':
                if not allow_signature or text.strip() != '{{instructor_signature}}':
                    raise ValueError('Invalid signature image')
            elif 'instructor_signature' in names:
                raise ValueError('Signature must be an image field')
            remainder = PLACEHOLDER_RE.sub('', text)
            if '{{' in remainder or '}}' in remainder:
                raise ValueError('Invalid placeholder syntax')
            for key in ('x', 'y', 'width', 'height', 'font_size'):
                number = item.get(key)
                if isinstance(number, bool) or not isinstance(number, (float, int)) or not math.isfinite(number):
                    raise ValueError('Invalid size or position')
            if not (0 <= item['x'] <= 100 and 0 <= item['y'] <= 100):
                raise ValueError('Position outside page')
            if not (0 < item['width'] <= 100 and 0 < item['height'] <= 100):
                raise ValueError('Invalid box size')
            if item['x'] + item['width'] > 100.01 or item['y'] + item['height'] > 100.01:
                raise ValueError('Box outside page')
            if not 4 <= item['font_size'] <= 96:
                raise ValueError('Invalid font size')
            if item.get('align') not in ('left', 'center', 'right'):
                raise ValueError('Invalid alignment')
            if not isinstance(item.get('bold'), bool):
                raise ValueError('Invalid font weight')
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', item.get('color', '')):
                raise ValueError('Invalid text color')
        return items
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError(_lt("Invalid PDF field layout. Check the text, positions and sizes in the PDF designer.")) from exc


def certificate_font(bold=False):
    """Embed Odoo's existing Unicode font; no new system dependencies."""
    name = 'EventCertificateBold' if bold else 'EventCertificate'
    if name not in pdfmetrics.getRegisteredFontNames():
        filename = 'Lato-Bol-webfont.ttf' if bold else 'Lato-Reg-webfont.ttf'
        with file_open('web/static/fonts/lato/' + filename, 'rb') as font_file:
            pdfmetrics.registerFont(TTFont(name, io.BytesIO(font_file.read())))
    return name


def wrap_text(text, font, size, width):
    """Wrap text without interpreting it as HTML; preserve explicit topic lines."""
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for word in paragraph.split():
            candidate = (line + ' ' + word).lstrip()
            if pdfmetrics.stringWidth(candidate, font, size) <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
                line = ''
            # Split long unbroken names instead of running beyond the box.
            for char in word:
                if line and pdfmetrics.stringWidth(line + char, font, size) > width:
                    lines.append(line)
                    line = ''
                line += char
        lines.append(line)
    return lines


def render_pdf_background(reader, items, rows, empty_message):
    """Shared vector-preserving renderer for certificates and signup sheets."""
    # PDF.js uses the rotated CropBox. Match that visible origin and size.
    background = copy.deepcopy(reader.pages[0])
    background.transfer_rotation_to_content()
    box = background.cropbox
    width, height = float(box.width), float(box.height)
    left, bottom = float(box.left), float(box.bottom)
    from PyPDF2 import Transformation
    background.add_transformation(Transformation().translate(-left, -bottom))
    background.mediabox.lower_left = (0, 0)
    background.mediabox.upper_right = (width, height)
    background.cropbox.lower_left = (0, 0)
    background.cropbox.upper_right = (width, height)
    if '/Annots' in background:
        del background['/Annots']
    writer = PdfWriter()
    for values in rows or [None]:
        overlay = io.BytesIO()
        drawing = canvas.Canvas(overlay, pagesize=(width, height))
        if values is None:
            drawing.setFont(certificate_font(), 12)
            drawing.drawString(30, height - 40, str(empty_message))
        else:
            for item in items:
                x, top = item['x'] * width / 100, item['y'] * height / 100
                box_width, box_height = item['width'] * width / 100, item['height'] * height / 100
                if item.get('kind') == 'image':
                    signature = values.get('instructor_signature')
                    if signature:
                        try:
                            image = ImageReader(io.BytesIO(base64.b64decode(signature)))
                            drawing.drawImage(image, x, height - top - box_height,
                                              width=box_width, height=box_height,
                                              preserveAspectRatio=True, anchor='c', mask='auto')
                        except Exception as exc:
                            raise UserError(_lt("The instructor signature image could not be read. Please upload it again on the track or instructor contact.")) from exc
                    continue
                text = PLACEHOLDER_RE.sub(lambda match: values[match.group(1)], item['template'])
                font = certificate_font(item['bold'])
                size = item['font_size']
                while True:
                    lines = wrap_text(text, font, size, box_width)
                    if (len(lines) * size * 1.2 <= box_height
                            and all(pdfmetrics.stringWidth(line, font, size) <= box_width for line in lines)):
                        break
                    if size <= 4:
                        raise UserError(_lt("The field '%(field)s' will not fit for %(company)s. Enlarge its box in the PDF designer.", field=item['template'], company=values.get('company') or values.get('event_name', '')))
                    size = max(4, size - 0.5)
                drawing.setFont(font, size)
                drawing.setFillColor(HexColor(item['color']))
                ascent = pdfmetrics.getAscent(font) / 1000
                descent = -pdfmetrics.getDescent(font) / 1000
                baseline = height - top - (ascent + (1.2 - ascent - descent) / 2) * size
                for line in lines:
                    line_width = pdfmetrics.stringWidth(line, font, size)
                    offset = {'left': 0, 'center': (box_width - line_width) / 2,
                              'right': box_width - line_width}[item['align']]
                    drawing.drawString(x + offset, baseline, line)
                    baseline -= size * 1.2
        drawing.save()
        page = copy.deepcopy(background)
        page.merge_page(PdfReader(overlay).pages[0])
        writer.add_page(page)
    result = io.BytesIO()
    writer.write(result)
    return result.getvalue()


class EventCertificatePdf(models.Model):
    _inherit = 'event.event'

    certificate_pdf = fields.Binary(
        string='Certificate PDF', attachment=True, copy=True,
        help="Upload a single-page PDF background, then position fields below. "
             "This takes precedence over HTML certificate templates. Maximum size: 20 MB.",
    )
    certificate_pdf_filename = fields.Char(string='Certificate PDF filename')
    certificate_pdf_layout = fields.Text(string='Certificate field positions', copy=True)

    @api.constrains('certificate_pdf')
    def _check_certificate_pdf(self):
        for event in self.with_context(bin_size=False):
            if event.certificate_pdf:
                read_background(event.certificate_pdf)

    @api.constrains('certificate_pdf_layout')
    def _check_certificate_pdf_layout(self):
        for event in self:
            read_layout(event.certificate_pdf_layout)

    def get_certificate_pdf_preview_values(self):
        """Sample actual event data for the designer; normal access rules apply."""
        self.ensure_one()
        self.check_access('read')
        return self._certificate_pdf_values((self._get_attendee_companies() or ['Company name'])[0])

    def _certificate_pdf_values(self, company):
        self.ensure_one()
        return {
            'company': company or '',
            'event_name': self.name or '',
            'event_date': self._get_certificate_event_date(),
            'topics': '\n'.join(self._get_certificate_topics()),
            'presented_by': self._get_certificate_presented_by(),
        }

    def _render_pdf_certificates(self):
        """Stamp text on the original PDF, retaining its artwork and page dimensions."""
        self.ensure_one()
        self.check_access('read')
        event = self.with_context(bin_size=False)
        reader = read_background(event.certificate_pdf)
        items = read_layout(event.certificate_pdf_layout)
        companies = event._get_attendee_companies()
        if companies and not items:
            raise UserError(_("Add at least one field to the certificate PDF designer, then save the event before printing."))

        return render_pdf_background(
            reader, items, [event._certificate_pdf_values(company) for company in companies],
            _('No company could be determined from the attendees.'),
        )
