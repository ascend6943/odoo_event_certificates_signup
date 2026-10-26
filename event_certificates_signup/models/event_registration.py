# -*- coding: utf-8 -*-
from odoo import models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    def _get_certificate_company_name(self):
        """Return the company name to print on certificates and signup sheets.

        Resolution order (first non-empty value wins):

        1. the registration ``company_name`` (standard attendee field),
        2. the parent company of the attendee contact,
        3. the company name of the attendee contact,
        4. the attendee partner name when the partner is a company.

        Returns ``False`` when no company can be determined, so that the
        reports can skip the attendee gracefully.
        """
        self.ensure_one()
        registration_name = self.name and self.name.strip()
        company_name = self.company_name and self.company_name.strip()
        if company_name and company_name != registration_name:
            return company_name

        partner = self.partner_id
        if partner:
            if partner.parent_id and partner.parent_id.name:
                return partner.parent_id.name.strip()
            partner_company = partner.company_name and partner.company_name.strip()
            if partner_company and partner_company != (partner.name or '').strip():
                return partner_company
            if partner.is_company and partner.name:
                return partner.name.strip()
        return company_name or False
