# -*- coding: utf-8 -*-
import io

from odoo import models
from odoo.tools.pdf import PdfReader, PdfWriter


class CertificateActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report = self._get_report(report_ref)
        ids = [res_ids] if isinstance(res_ids, int) else res_ids
        report_config = {
            'event_certificates_signup.company_certificate_report': ('certificate_pdf', '_render_pdf_certificates'),
            'event_certificates_signup.signup_sheet_report': ('signup_sheet_pdf', '_render_pdf_signup_sheets'),
        }.get(report.report_name)
        if not report_config or not ids:
            return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

        pdf_field, render_method = report_config

        events = self.env['event.event'].browse(ids)
        events.check_access('read')
        if not any(events.mapped(pdf_field)):
            return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

        # Both the event button and the standard Print menu use this report.
        # Mixed selections keep each event's own PDF/HTML/default layout.
        writer = PdfWriter()
        for event in events:
            if event[pdf_field]:
                content = getattr(event, render_method)()
            else:
                content, _kind = super(CertificateActionsReport, self.with_context(
                    force_report_rendering=True,
                ))._render_qweb_pdf(report_ref, res_ids=event.ids, data=data)
            for page in PdfReader(io.BytesIO(content), strict=False).pages:
                writer.add_page(page)
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue(), 'pdf'
