# Event Certificates & Signup Sheets

An Odoo 19 addon for printing company attendance certificates and topic-specific signup sheets from Events.

**Technical name:** `event_certificates_signup`  
**License:** LGPL-3.0  
**Author:** Dawayne Safety Consulting

## Features

- **Company certificates:** one certificate per distinct company represented by the event's attendees, listing the event date and training topics.
- **Topic signup sheets:** one sheet per company and topic, with training details, instructor information, signature image, and blank attendance lines.
- Case-insensitive company deduplication.
- Optional HTML certificate templates with placeholders for event and company details.
- Instructor signature images on tracks, with a contact-level fallback.
- US Letter landscape certificates and portrait signup sheets.

The addon extends standard Odoo Events models without changing the attendee workflow. Topics are event tracks.

## Requirements

- Odoo **19**, Community or Enterprise, with access to install custom addons.
- Odoo modules `event` and `website_event_track`.
- A working `wkhtmltopdf` installation for PDF reports, available to the Odoo service. Use an Odoo-compatible build with patched Qt.

No additional Python packages beyond Odoo's normal dependencies are required. Other Odoo versions are not claimed to be supported.

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

### Instructor signatures

Upload an **Instructor Signature** on the event track, or on the instructor's contact as a fallback. A transparent-background PNG is recommended. Missing signatures do not prevent printing.

### Custom certificate templates

Open the event's **Certificates** tab and fill in **Certificate Template (HTML)**. Leave it empty to use the default layout.

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

Templates use HTML, not uploaded Word or PDF documents. Odoo sanitizes the HTML on save.

## Troubleshooting

- **Addon not visible:** verify `addons_path`, directory permissions, and the `event_certificates_signup` folder name; restart Odoo and update the apps list.
- **PDF generation fails:** check `wkhtmltopdf --version` on the Odoo server and try another standard Odoo PDF report. The PDF engine is a server dependency and is not bundled in this repository.
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

The included tests cover company resolution and deduplication, report data, custom placeholders, and HTML template rendering. HTML rendering tests do not verify the destination server's PDF engine.

## Limitations

- Certificates list event topic titles, not verified per-attendee attendance for each topic.
- Signup sheets contain blank attendance lines rather than a prefilled attendee roster.
- If no instructor can be resolved, instructor details remain blank.

See the [module documentation](event_certificates_signup/README.md) for additional details.
