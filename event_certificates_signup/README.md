# Event Certificates & Signup Sheets

Adds two printable documents to Odoo Events for a safety training company:

1. **Company Certificate** – one certificate per company represented among the
   event attendees (companies are deduplicated), showing the company name, the
   event date and the titles of the topics presented (event tracks).
2. **Topic Signup Sheet** – one sheet per company **and** per topic (event
   track), showing the company, event date, topic, start/finish times and the
   instructor name, plus the instructor signature image and a blank attendance
   area.

The module is built entirely on the standard `event.event`,
`event.registration` and `event.track` models. The standard attendee workflow
is **not** modified.

## Requirements

- Odoo 19 (Community or Enterprise)
- `event` and `website_event_track` (the "Events" and "Advanced Events" apps)
- `wkhtmltopdf` (standard Odoo dependency for PDF reports)

No extra Python package is required.

## Installation

The module lives in the custom addons path already configured in
`/opt/odoo/config/odoo.conf` (`/opt/odoo/custom-addons`).

From the Odoo UI: **Apps → Update Apps List → search "Event Certificates" →
Install**.

From the command line:

```bash
sudo -u odoo /opt/odoo/venv/bin/python3 /opt/odoo/odoo/odoo-bin \
    -c /opt/odoo/config/odoo.conf -d <database> \
    -i event_certificates_signup --stop-after-init --no-http
```

Then restart the Odoo service.

## Configuration

### Instructor signature (transparent-background PNG)

There are two places to upload the instructor signature:

- **On the event track** (recommended): *Events → Tracks → open a track →
  Speaker tab → Instructor Signature*. This is the exact instructor of the
  topic.
- **On the instructor contact**: *Contacts → open the instructor → Sales &
  Purchase tab → Instructor Signature*. Used as a fallback when a track has no
  signature of its own.

Upload a PNG with a transparent background for the best result.

### Optional certificate template (HTML)

Each event has an optional **Certificates** tab with a
**Certificate Template (HTML)** field. When empty, the default certificate
layout is used. When filled, the template is rendered once per attending
company.

Available placeholders:

| Placeholder        | Replaced with                                        |
| ------------------ | ---------------------------------------------------- |
| `{{company}}`      | the attending company name                           |
| `{{event_name}}`   | the event name                                       |
| `{{event_date}}`   | the event date (or date range)                       |
| `{{topics}}`       | an HTML `<ul>` list of the presented topic titles    |
| `{{presented_by}}` | the organizer issuing the certificate                |

Example:

```html
<div style="text-align:center; padding:20mm;">
    <h1>Certificate of Attendance</h1>
    <h2>{{company}}</h2>
    <p>Took part in the safety training on {{event_date}}.</p>
    {{topics}}
    <p style="margin-top:30mm;">{{presented_by}}</p>
</div>
```

Why HTML and not a `.docx`/PDF upload? Odoo reports are rendered through QWeb
(HTML + CSS). An uploaded binary template cannot be bidirectionally merged with
live data in a reliable, supported way. A sanitized HTML template with
placeholders is the maintainable Odoo-native alternative and can be styled to
match any letterhead. If a fixed background image is required, add it as a
background in the HTML template.

### Paper format

The module ships two paper formats (matching the provided samples):

- **Certificate (US Letter Landscape)** – for the certificate report.
- **Signup Sheet (US Letter Portrait)** – for the signup sheet report.

They are assigned to the report actions and can be changed under
*Settings → Technical → Reporting → Paper Formats* and
*Settings → Technical → Actions → Reports* if A4 is preferred.

## Usage

### From the event form

Open an event and use either:

- the **Company Certificates** / **Signup Sheets** stat buttons (top right), or
- the gear menu → **Print → Company Certificates / Signup Sheets**, or
- the gear menu → **Generate Company Certificates / Generate Signup Sheets**
  (wizard, allows confirming the event).

The reports are also available from the **Print** menu of the events list view.

Both buttons open a wizard that lets you confirm the event before printing; the
report then generates:

- one certificate per distinct company, and
- one signup sheet per (company × topic).

### Data used

- **Companies** come from the event attendees
  (`event.registration.company_name`, falling back to the attendee's parent
  company, `company_name` and, for company partners, the partner name).
  Companies are deduplicated case-insensitively and registrations in state
  *Cancelled* are ignored.
- **Topics** come from the active event tracks.
- **Instructor** comes from the track speaker (falling back to the responsible
  user). The signature comes from the track, then from the speaker contact.
- **Times** come from the track start/end, falling back to the event dates.

## Tests

```bash
sudo -u odoo /opt/odoo/venv/bin/python3 /opt/odoo/odoo/odoo-bin \
    -c /opt/odoo/config/odoo.conf -d <database> \
    -u event_certificates_signup --test-enable \
    --test-tags /event_certificates_signup --stop-after-init --no-http
```

The tests cover company resolution and deduplication (including cancelled
registrations and attendees without a company) and the data and templates of
both reports.

## Known limitations

- The certificate lists the **titles** of the topics, not per-attendee
  attendance per topic.
- If a track has no instructor, the instructor name is left blank and no
  signature is printed; the rest of the sheet is still generated.
- If no company can be resolved for any attendee, the signup report still
  generates one sheet per topic with a blank company field, and the certificate
  report prints an informational page.
- The HTML certificate template is sanitized by Odoo on save; scripts and event
  handlers are removed.
