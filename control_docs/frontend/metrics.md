# Frontend metrics (GA4)

The Streamlit app sends browser-side events to GA4 using the web measurement ID
`G-9ZHLKD65GM` (web stream ID `16319805930`). The stream ID is an identifier in
the Google Analytics administration UI, not a credential and not part of event
requests. No Measurement Protocol secret or server-side analytics calls are used.
The component and event producers live in `frontend/metrics.py` and
`frontend/components/metrics_client/`.

For the exact GA4 screens, custom-dimension names, and verification steps, use
the [Google Analytics setup checklist](google_analytics_setup.md).

## Configuration and deployment

- The canonical app URL is `BASE_URL` in `system_common/UrlPaths.py`; it defaults
  to `https://eitz-habina.fly.dev/`. Set `EITZ_HABINA_BASE_URL` to change it
  without editing code. It also controls generated links and the only origin
  on which the analytics component sends events. Include the scheme and, if
  applicable, the port. Configure this on the deployment when changing domains.
- Set `GA4_MEASUREMENT_ID` to override the default ID. An invalid ID disables
  tracking and is reported in the browser console.
- In GA4 Admin, select the web stream above and **disable enhanced measurement**,
  especially automatic page changes, site search and file downloads. The app
  sends these events itself. Disable any other Google tag or integration on the
  site: it could duplicate events, bypass the admin opt-out, or send unsanitized
  data. The tag is configured with `send_page_view: false` and Google signals
  disabled. The app does not configure the GA property remotely.
- Register the desired event-scoped custom dimensions in GA4 Admin (for example
  `app_language`, `came_from`, `search_type`, `text_similarity_used`,
  `entity_type`, `entity_id`, `entity_name`, `entity_types`, `entity_ids`,
  `entity_names`, `passage_types`, `source_types`, `tree_type`,
  `relationship_filter_used`, and `download_type`). GA4 standard-property
  quotas limit how many dimensions can be registered; prioritize the reports
  you need. `page_location` and the standard `file_download` event are built in.
  Custom fields can also be inspected in DebugView or explored after registration.
- Evaluate applicable cookie/consent requirements for your deployment. This
  implementation does not provide a consent banner or consent-mode integration.

## Admin opt-out

Open `https://eitz-habina.fly.dev/?admin=true` before starting an admin session.
The app propagates `admin=true` or `admin=false` through its navigation, search
URL rewrites, home link, and relationship-source links. The browser remembers
the setting in **sessionStorage for this tab**, including a reload or a
same-origin navigation that omitted the parameter; it restores the parameter
to the URL. `admin=false` explicitly re-enables tracking in that tab. A fresh
tab without an admin URL has its own setting. Invalid or repeated conflicting
values fail closed as `admin=true`. This is an analytics exclusion, **not**
authentication or access control.

When opted out, the Python event queue is suppressed where the setting is known;
the browser independently checks both the URL and stored setting before loading
the tag or sending each event. No GA tag is loaded in a fresh opted-out page.
If the setting changes after a tag was loaded, the GA disable flag is set before
subsequent events. Blocking session storage or otherwise preventing the opt-out
check disables tracking and reports the error in the browser console.

## Events

Every app-produced event includes `app_language` (`en` or `he`) and a sanitized
`page_location`. Events are best-effort: a blocked tag, network error, browser
shutdown, or navigation before delivery can lose events. There is no retry
queue or delivery guarantee.

| Event | When | Additional parameters |
|---|---|---|
| `page_view` | Initial page and each distinct browser URL, including search-URL changes. Ordinary Streamlit reruns do not add views. | `came_from` when known: previous app path and a recognized control, or `entity_relationship_sources` for the relationship link opened in a new tab. Direct visits normally have no `came_from`. |
| `app_search` | Source, number, unit, entity and tree-person searches, including searches executed from supported shared URLs. Pagination is not another search. | `search_type`; source searches: `search_id`, `text_similarity_used` (0/1), `passage_types`, `source_types`, `entity_types`, `entity_ids`, `entity_names`, `relationship_filter_used` (0/1); number: `number_value`; unit: `unit_name`; entity: `entity_types`, `entity_ids`, `entity_names`; tree: `tree_type`, `entity_type`, `entity_id`, `entity_name`. |
| `search_entity_filter` | Once per selected entity option in a source search. | `search_id` joins this to its `app_search`; `entity_type`, `entity_id` and canonical English `entity_name` identify the selection even when the summary lists are truncated. |
| `file_download` | The source-results PDF download button is clicked. | `file_type=pdf`, `download_type=source_results`. This records a click, not proof that the PDF was saved. |

Entity IDs and names come from the app's selected database options; grouped
number options represent the selected option, not every underlying database ID.
Relationship search is recorded as a boolean; arbitrary relationship IDs and
labels from incoming URLs are not sent. Text fields are capped at 100 characters
to respect GA4 parameter limits, so comma-separated summary lists can be
truncated. Entity-filter events retain individual selections. Searches initiated
by buttons are recorded even if the same URL is searched again; a page view
requires a URL change.

## Privacy and URL handling

GA4 prohibits sending URLs or search input containing personally identifiable
information. Consequently, the app does **not** send a literal full URL:
`page_location` includes the actual origin and known page path, plus only a
strictly numeric number/fraction search, when applicable. It removes free text,
entity and relationship query parameters, `admin`, unknown parameters, and URL
fragments. Source text is represented solely by `text_similarity_used`; it is
never sent as an event field. Validated filter metadata is sent separately as
described above. The referrer sent to GA is reduced to an origin, without its
path or query; if unavailable it is the app origin. This sacrifices detailed
referrer information for privacy. `via=entity_relationship_sources` is a
non-sensitive navigation hint for links that open a new tab and is not included
in `page_location`.

GA4 also collects its usual automatic information independently of these custom
fields; consult Google's property settings and privacy documentation. Analytics
is intended to measure application usage, not to capture personal search text.
Entity names are public database content, not the visitor's identity.

## Verification

Run the frontend regression tests from the project root:

```powershell
.\venv\Scripts\python.exe -m unittest frontend.tests.test_metrics frontend.tests.test_navigation_menu frontend.tests.test_selector_fragments frontend.tests.test_source_search_pdf frontend.tests.test_entity_relationships
node --test frontend\tests\test_metrics_client.js
```

For browser testing without sending real data, run
`frontend/tests/metrics_fixture.py` with Streamlit, set `EITZ_HABINA_BASE_URL`
to its localhost origin, and intercept the `googletagmanager.com` script.
Check the iframe's `dataLayer`: normal navigation, search, and PDF clicks should
emit the events above; the entered free text must not appear. Repeat with
`?admin=true`: navigation and reload must retain the setting and the Google tag
must not be loaded. A real GA4 DebugView check on the deployed property is still
needed after deployment and GA4 configuration.
