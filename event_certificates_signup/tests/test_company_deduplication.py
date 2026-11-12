# -*- coding: utf-8 -*-
from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestCompanyDeduplication(common.TransactionCase):
    """Ensure companies are correctly resolved and deduplicated."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event = cls.env['event.event'].create({
            'name': 'Fall Protection Training',
            'date_begin': '2026-10-08 14:00:00',
            'date_end': '2026-10-08 20:00:00',
            'date_tz': 'UTC',
        })
        # Two employees of the same company, declared through the parent company.
        cls.company_a = cls.env['res.partner'].create({
            'name': 'Company A',
            'is_company': True,
        })
        cls.employee_1 = cls.env['res.partner'].create({
            'name': 'John Doe',
            'parent_id': cls.company_a.id,
        })
        cls.employee_2 = cls.env['res.partner'].create({
            'name': 'Jane Smith',
            'parent_id': cls.company_a.id,
            'company_name': 'COMPANY A',  # same company, different spelling/case
        })
        # A company partner attending directly.
        cls.company_b = cls.env['res.partner'].create({
            'name': 'Company B',
            'is_company': True,
        })
        # An attendee without any company information.
        cls.lonely_partner = cls.env['res.partner'].create({'name': 'Anonymous Guest'})

        for partner in (cls.employee_1, cls.employee_2, cls.company_b, cls.lonely_partner):
            cls.env['event.registration'].create({
                'event_id': cls.event.id,
                'partner_id': partner.id,
                'name': partner.name,
            })

    def _registration(self, partner):
        return self.env['event.registration'].search([
            ('event_id', '=', self.event.id),
            ('partner_id', '=', partner.id),
        ], limit=1)

    def test_company_deduplication(self):
        companies = self.event._get_attendee_companies()
        # Company A is present only once despite two attendees and two spellings.
        self.assertEqual(len([c for c in companies if c.casefold() == 'company a']), 1)
        self.assertTrue(any(c.casefold() == 'company a' for c in companies))
        self.assertTrue(any(c.casefold() == 'company b' for c in companies))
        # The attendee without company must not create a bogus entry.
        self.assertFalse(any('anonymous' in c.casefold() for c in companies))

    def test_company_resolution_from_parent(self):
        self.assertEqual(self._registration(self.employee_1)._get_certificate_company_name(),
                          'Company A')

    def test_company_resolution_for_company_partner(self):
        self.assertEqual(self._registration(self.company_b)._get_certificate_company_name(),
                          'Company B')

    def test_no_company_returns_false(self):
        self.assertFalse(self._registration(self.lonely_partner)._get_certificate_company_name())

    def test_cancelled_registrations_are_ignored(self):
        registration = self._registration(self.company_b)
        registration.state = 'cancel'
        companies = self.event._get_attendee_companies()
        self.assertFalse(any(c.casefold() == 'company b' for c in companies))
