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

### PDF certificate designer (recommended)

1. Open an event → **Certificates**.
2. Upload a **single-page PDF** in **Certificate PDF** (maximum 20 MB; no password protection).
   Use a clean certificate with blank spaces for variable details. Existing printed
   text in the PDF is not erased or replaced. The PDF need not contain form fields.
3. Click **{{company}}**, **{{event_name}}**, **{{event_date}}**, **{{topics}}** or
   **{{presented_by}}** to add a positioned field. Drag it on the PDF to place it.
4. Click a field to edit its text, font size, bold, color and alignment in the
   right-hand panel. Text can combine labels and placeholders, e.g. `Date: {{event_date}}`.
   Drag the bottom-right handle to resize the field's box. Positions and box sizes
   can also be entered as percentages of the visible page. Arrow keys move the
   focused field by 0.1%; Shift + arrow moves by 1%.
5. **Show event data** previews the first attending company's values for the saved
   event. **Save & test print** saves the current background/positions and downloads
   the real certificates. Use this for the definitive layout check.
6. Print using the existing **Company Certificates** button or **Print** menu.

The original PDF is stamped directly, not converted through HTML. Its artwork,
page size and orientation are retained, including rotated/cropped PDFs. There is
one page per case-insensitively deduplicated attending company. Topics wrap onto
separate lines. Text shrinks as needed to fit its box; if it cannot fit even at
4 pt, printing asks you to enlarge the box rather than silently omitting text.
The editor displays the chosen font size; use test print to check auto-fitted text.

A PDF takes precedence over HTML certificate templates. Remove the PDF to return
to the existing HTML/default layout; saved HTML and field positions are retained.
Signup sheets have their own independent PDF designer below. This is an overlay
designer, not an editor for existing text/artwork inside the uploaded PDF.

No additional packages are needed: PDF.js, PyPDF2 and ReportLab are already part
of this Odoo installation. The module embeds Odoo's existing Lato font for Unicode
company names. Always save your event after making positioning changes.

### PDF signup sheet designer

1. Open an event → **Signup Sheets** and upload **Signup Sheet PDF**.
   Use a single-page PDF (maximum 20 MB, no password protection). Include your
   attendance table/blank signature lines in the uploaded design; these are
   preserved as part of the background, not populated from registrations.
2. Add and drag fields exactly as in the certificate designer. Available fields:
   `{{company}}`, `{{event_name}}`, `{{event_date}}`, `{{topic}}`, `{{start_time}}`,
   `{{finish_time}}`, `{{instructor}}`, `{{instructor_signature}}`, `{{presented_by}}`.
3. **{{instructor_signature}}** adds an image box, not a text/data-URI field.
   Drag and resize it to fit the instructor's signature. The PNG's transparency
   and proportions are preserved. It uses the track signature first, then the
   instructor contact's signature, and is left blank if neither is available.
4. **Show event data** previews the first company/topic (including its signature)
   from the saved event. **Save & test print** saves the current design and prints
   all signup sheets, using each topic's own instructor, signature and times.
5. The existing **Signup Sheets** button and **Print → Signup Sheets** use
   the PDF automatically. Text formatting, exact percentage positions, resizing,
   wrapping and auto-fit work like certificates.

One page is produced per **unique company × active topic/track**. For example,
three companies attending two topics produce **six pages**. Companies are
deduplicated case-insensitively; cancelled registrations and inactive tracks are
excluded. With no resolvable companies, a blank-company sheet is still generated
per topic. With no active topics, an information page is returned. Track times
use the event's display timezone. Missing instructor details are left blank.

The signup PDF and its positions are separate from the certificate design.
Removing the signup PDF returns signup printing to its existing HTML/default
layout; it does not delete the saved HTML or PDF field positions.

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
**Certificate Template (HTML source)** field. When empty, the default
certificate layout is used. When filled, the template is rendered once per
attending company.

The template is a plain-text field, so a **complete HTML document** (including
its own `<style>` block) can be pasted as-is. The report extracts the styles and
the `<body>` content before rendering, so you do not have to trim the document
envelope yourself.

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
<!DOCTYPE html>
<html>
<head>
  <style>
    .certificate { text-align: center; padding: 20mm; border: 8px solid #1f3b63; }
    .certificate h1 { color: #1f3b63; }
  </style>
</head>
<body>
  <div class="certificate">
    <h1>Certificate of Attendance</h1>
    <h2>{{company}}</h2>
    <p>Took part in the safety training on {{event_date}}.</p>
    {{topics}}
    <p style="margin-top:30mm;">{{presented_by}}</p>
  </div>
</body>
</html>
```

### Optional signup sheet template (HTML)

Each event has an optional **Signup Sheets** tab with a
**Signup Sheet Template (HTML source)** field. It works exactly like the
certificate template, but is rendered once per **(company, topic)** pair.

Available placeholders:

| Placeholder               | Replaced with                                             |
| ------------------------- | --------------------------------------------------------- |
| `{{company}}`             | the attending company name                                |
| `{{event_name}}`          | the event name                                            |
| `{{event_date}}`          | the event date (or date range)                            |
| `{{topic}}`               | the topic (track) title                                   |
| `{{start_time}}`          | the topic start time                                      |
| `{{finish_time}}`         | the topic finish time                                     |
| `{{instructor}}`          | the instructor name (blank when unknown)                  |
| `{{instructor_signature}}`| the instructor signature as a data URI, for use in `<img src>` |
| `{{presented_by}}`        | the organizer issuing the sheet                           |

Example:

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    .sheet { padding: 15mm; }
    .sheet h2 { color: #2d6cdf; }
    .sig { height: 15mm; }
  </style>
</head>
<body>
  <div class="sheet">
    <h2>{{topic}}</h2>
    <p><strong>{{company}}</strong> — {{event_date}}</p>
    <p>{{start_time}} – {{finish_time}}</p>
    <p>Instructor: {{instructor}}</p>
    <img class="sig" src="{{instructor_signature}}"/>
    <p>By signing, I acknowledge that I attended this session.</p>
    <!-- add your own attendance table here -->
  </div>
</body>
</html>
```

`{{instructor_signature}}` expands to a complete `data:image/...;base64,...`
URI when a signature is available, and to an empty string otherwise, so an
`<img src="{{instructor_signature}}"/>` degrades gracefully when no signature
has been uploaded.

> **Put the signature in an `src` attribute.** The signature placeholder is
> only expanded when it is used as an attribute value, e.g.
> `<img src="{{instructor_signature}}"/>`. Written as plain text
> (`<span>{{instructor_signature}}</span>`) it resolves to nothing, so a wall of
> base64 text is never printed into the document.

> **Pasting from Word/Outlook.** Exported Word HTML is full of `&nbsp;`
> entities and `mso-` styles. These are preserved (the `mso-` styles are simply
> ignored by the renderer) and the whitespace entities are normalised to plain
> spaces, so no stray `Â` characters appear in the PDF.

Why HTML and not a `.docx`/PDF upload? Odoo reports are rendered through QWeb
(HTML + CSS). An uploaded binary template cannot be bidirectionally merged with
live data in a reliable, supported way. A plain-text HTML template with
placeholders is the maintainable Odoo-native alternative and can be styled to
match any letterhead. If a fixed background image is required, add it as a
background in the HTML template.

> **Legacy rich-text fields.** The older `Certificate Template (rich text)` and
> `Signup Sheet Template (rich text)` fields are still supported as a fallback
> (under the *Advanced* group, visible to technical users). Prefer the plain
> HTML source fields: the Odoo rich-text sanitizer escapes pasted markup and
> mangles CSS.

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
