# -*- coding: utf-8 -*-
from odoo import fields, models


class EventTrack(models.Model):
    _inherit = 'event.track'

    instructor_signature = fields.Image(
        string='Instructor Signature',
        max_width=1024,
        max_height=1024,
        help="Upload the instructor signature as a transparent-background PNG. "
             "It is printed on the topic signup sheets.",
    )

    def _get_instructor_name(self):
        """Return the instructor name to print on the signup sheet.

        Falls back on the responsible user when no speaker is set on the track,
        and returns an empty string when no instructor can be determined.
        """
        self.ensure_one()
        return (
            (self.partner_name or '').strip()
            or (self.partner_id.name or '').strip()
            or (self.user_id.name or '').strip()
        )

    def _get_instructor_signature(self):
        """Return the signature image (base64) for the track instructor.

        Falls back on the speaker partner signature when the track does not
        define its own signature image.
        """
        self.ensure_one()
        return self.instructor_signature or self.partner_id.instructor_signature or False
