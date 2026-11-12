# Event Certificates & Signup Sheets

An Odoo 19 addon for printing company attendance certificates and topic-specific signup sheets from Events.

- **Technical name:** `event_certificates_signup`
- **Module version:** `19.0.1.2.0`
- **License:** LGPL-3.0

## Features

- **Company certificates:** one certificate per distinct company represented by the event's attendees, listing the event date and training topics.
- **Topic signup sheets:** one sheet per company and topic, with training details, instructor information, signature image, and blank attendance lines.
- **Independent PDF designers:** upload a certificate or signup sheet background, then drag and resize text fields or an instructor signature image on the page.
- Text formatting (font size, bold, color, alignment), percentage-based positions, keyboard positioning, wrapping, and automatic text fitting.
- **Show event data** previews saved event values; **Save & test print** saves the design and generates the actual reports.
- Direct PDF overlays preserve background artwork, page size, and orientation, including rotated/cropped pages.
- Case-insensitive company deduplication.
- Optional HTML source templates for **both** reports, accepting complete HTML documents and CSS, with legacy rich-text fallback.
- Instructor signature images on tracks, with a contact-level fallback.
- Default HTML layouts use US Letter landscape certificates and portrait signup sheets; uploaded PDFs retain their own page dimensions.

The addon extends standard Odoo Events models without changing the attendee workflow. Topics are event tracks.

## Requirements

- Odoo **19**, Community or Enterprise, with access to install custom addons.
- Odoo modules `event` and `website_event_track`.
- Python packages **PyPDF2** and **ReportLab**, declared in the addon manifest and available in the Odoo service's Python environment. They may already be installed with Odoo; verify them before installing or upgrading the addon.
- Odoo's bundled **PDF.js** assets for the browser designer and **Lato** fonts for PDF text. No separate PDF.js installation is needed.
- A working `wkhtmltopdf` installation for HTML/default reports, available to the Odoo service. Use an Odoo-compatible build with patched Qt. Uploaded-PDF overlays are generated directly with PyPDF2 and ReportLab instead.

If the Python packages are missing, install them using your deployment's dependency-management process in the same environment that runs Odoo. Other Odoo versions are not claimed to be supported.

## Installation

1. Clone this repository into a directory readable by the Odoo service:

   ```bash
   git clone https://github.com/ascend6943/odoo_event_certificates_signup.git
   ```

2. Add the **repository directory** to `addons_path` in your Odoo configuration, preserving all existing paths. For example:

   ```ini
   addons_path = /path/to/odoo/addons,/path/to/odoo_event_certificates_signup
   ```

   Alternatively, copy the inner `event_certificates_signup/` directory into an existing custom addons directory. Keep that directory name unchanged.

3. Restart Odoo, enable developer mode, and select **Apps → Update Apps List**.
4. Search for **Event Certificates & Signup Sheets** and install it. Remove the default **Apps** filter if the addon is not shown.

For a ZIP download from GitHub, extract the archive first and use the inner `event_certificates_signup/` folder—not the repository wrapper—as the addon.

### Command-line installation or upgrade

Using your deployment's Odoo executable, configuration, service account, and database:

```bash
odoo-bin -c /path/to/odoo.conf -d DATABASE \
  -i event_certificates_signup --stop-after-init --no-http
```

For an existing installation, replace `-i` with `-u`. Run this during a maintenance window with the regular Odoo service stopped, then restart the service afterward. Back up the database before upgrading.

## Usage

1. Create or open an event.
2. Add attendees with company information or contacts linked to a company.
3. Add event tracks for the training topics, including their times and instructors.
4. Use **Print → Company Certificates** or **Print → Signup Sheets** from the event's action menu.

The event form also provides **Company Certificates** and **Signup Sheets** buttons that open selection wizards. Reports are available from the events list's Print menu as well.

Only active registrations in the registered (`open`) or attended (`done`) states are used. Company names are deduplicated case-insensitively. The company is resolved from the registration and associated contact information.

### PDF certificate and signup sheet designers

1. Open an event's **Certificates** or **Signup Sheets** tab and upload **Certificate PDF** or **Signup Sheet PDF**.
2. Use a **single-page, unencrypted PDF, maximum 20 MB**, with blank spaces for variable details. For signup sheets, include the attendance table and blank signature lines in the background itself.
3. Click a placeholder button to add a field. Drag it into place and use its bottom-right handle to resize the box. In the side panel, edit the text, font size, bold, color, alignment, and exact positions/sizes as percentages of the page.
4. Combine labels and placeholders in text fields, such as `Date: {{event_date}}`. Arrow keys move a focused field by **0.1%**; **Shift + arrow** moves it by **1%**.
5. Use **Show event data** to preview the first company (and, for signup sheets, the first topic) from the saved event. Use **Save & test print** for the definitive printed layout, then print through the normal buttons or Print menu.

Each designer has its own background and saved field positions. An uploaded PDF takes priority over that report's HTML templates. Removing the PDF restores HTML/default printing without deleting saved HTML or field positions.

Text wraps and shrinks to fit its box. If it cannot fit even at **4 pt**, printing asks you to enlarge the box rather than silently dropping text. The browser preview shows the selected font size, so test print to check automatic fitting. At least one field must be configured when generating certificates for companies or signup sheets for topics.

Certificate PDFs produce one page per unique company. Signup PDFs produce one page per **company × active topic** (three companies and two topics produce six pages). If no company can be resolved, signup sheets still print once per topic with a blank company. Missing companies for certificates, or missing topics for signup sheets, produce an informational page.

This is an **overlay designer**, not an editor for existing PDF text or artwork. No PDF form fields are required. Uploaded Word documents are not supported.

### Instructor signatures

Upload an **Instructor Signature** on the event track, or on the instructor's contact as a fallback. A transparent-background PNG is recommended. Missing signatures do not prevent printing.

In the signup PDF designer, `{{instructor_signature}}` creates a resizable **image box**, not text. Its proportions and transparency are preserved, and it is left blank when no signature is available.

### Custom HTML templates

When no PDF is uploaded, use **Certificate Template (HTML source)** on the **Certificates** tab or **Signup Sheet Template (HTML source)** on the **Signup Sheets** tab. Leave the source empty to use a legacy rich-text template, if configured, or the default layout.

These plain-text source fields preserve HTML/CSS as entered. You can paste a complete HTML document with a `<style>` block; the report extracts its styles and body content. Use trusted template source only: these fields do **not** apply Odoo's rich-text sanitization. Ordinary event/company placeholder values are HTML-escaped.

Certificate placeholders:

| Placeholder | Value |
| --- | --- |
| `{{company}}` | Attending company name |
| `{{event_name}}` | Event name |
| `{{event_date}}` | Event date or date range |
| `{{topics}}` | HTML list of topic titles |
| `{{presented_by}}` | Organizer name, falling back to the event company |

```html
<div style="text-align:center; padding:20mm;">
    <h1>Certificate of Attendance</h1>
    <h2>{{company}}</h2>
    <p>Participated in {{event_name}} on {{event_date}}.</p>
    {{topics}}
    <p>Presented by {{presented_by}}</p>
</div>
```

Signup sheet placeholders:

| Placeholder | Value |
| --- | --- |
| `{{company}}` | Attending company name |
| `{{event_name}}` | Event name |
| `{{event_date}}` | Event date or date range |
| `{{topic}}` | Topic/track title |
| `{{start_time}}` | Topic start time |
| `{{finish_time}}` | Topic finish time |
| `{{instructor}}` | Instructor name, or blank |
| `{{instructor_signature}}` | Signature image data URI, for `<img src="{{instructor_signature}}"/>` |
| `{{presented_by}}` | Organizer name, falling back to the event company |

Track times use the event's display timezone, falling back to the user's timezone. In HTML, the signature placeholder must be used as a quoted attribute value, as in the example above. Used as plain text, it becomes blank rather than printing base64 image data. Whitespace entities from pasted Word/Outlook HTML are normalized to ordinary spaces.

The same placeholder names are available in each report's PDF designer, but `{{topics}}` is newline-separated text there, not an HTML list, and `{{instructor_signature}}` is an image box. PDF text fields do not interpret HTML.

Legacy **Certificate Template (rich text)** and **Signup Sheet Template (rich text)** fields remain under **Advanced** for technical users. The HTML source fields take precedence over them; prefer source fields to avoid rich-text sanitizer changes to pasted markup and CSS.

## Troubleshooting

- **Addon not visible:** verify `addons_path`, directory permissions, and the `event_certificates_signup` folder name; restart Odoo and update the apps list.
- **PDF upload or preview fails:** use a readable, single-page PDF without password protection, within the 20 MB limit. Verify Odoo's PDF.js assets are accessible; after upgrading, refresh the browser to reload backend assets.
- **Uploaded-PDF printing fails:** verify PyPDF2 and ReportLab in the Odoo Python environment. Add at least one field, save the event, and enlarge any field box named in an overflow error.
- **HTML/default PDF generation fails:** check `wkhtmltopdf --version` on the Odoo server and try another standard Odoo PDF report. This engine is a server dependency and is not bundled in this repository.
- **HTTP 500 or RPC error:** collect the Python traceback from the Odoo server log immediately after reproducing the problem. The browser error alone does not identify the cause. Include the Odoo version and whether other reports work when reporting an issue.
- **Missing styling or images:** check that the PDF renderer can reach Odoo's report assets and that the deployment's report/base URL settings are correct.
- **No companies or topics:** verify attendee company details and active tracks. Certificates show an informational page if no company can be resolved; signup sheets can use a blank company when topics exist.

## Tests

Run against a disposable Odoo test database with the required dependencies installed:

```bash
odoo-bin -c /path/to/odoo.conf -d TEST_DATABASE \
  -u event_certificates_signup --test-enable \
  --test-tags /event_certificates_signup --stop-after-init --no-http
```

The included tests cover company resolution and deduplication, report data, HTML source and legacy templates, placeholder/signature handling, PDF validation and overlays, page counts, rotated/cropped backgrounds, text fitting, previews, access checks, and HTML fallback. HTML rendering tests do not verify the destination server's `wkhtmltopdf` installation; use test prints to check the final layout and deployment.

## Limitations

- Certificates list event topic titles, not verified per-attendee attendance for each topic.
- Signup sheets contain blank attendance lines rather than a prefilled attendee roster.
- If no instructor can be resolved, instructor details remain blank.
- PDF backgrounds must be single-page and unencrypted; the designer cannot erase or replace existing background text/artwork.
- HTML source templates are trusted markup, not sandboxed or sanitized rich text.

See the [module documentation](event_certificates_signup/README.md) for additional details.
