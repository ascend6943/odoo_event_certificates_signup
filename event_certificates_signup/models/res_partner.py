# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    instructor_signature = fields.Image(
        string='Instructor Signature',
        max_width=1024,
        max_height=1024,
        help="Upload a transparent-background PNG signature for this instructor. "
             "It is used as a default on the topic signup sheets.",
    )
