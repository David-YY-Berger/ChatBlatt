# Google Analytics setup checklist for Eitz Habinah

This checklist is for configuring the **existing GA4 web stream** after the
analytics changes have been deployed. The application sends the events; you do
not need to create the events manually or paste another Google tag into the
site. The settings below must be made in Google Analytics; the application
cannot change them for you.

## 1. Open the correct property and stream

1. Sign in at [Google Analytics](https://analytics.google.com/).
2. Select the property that contains the Eitz Habinah website stream.
3. Open **Admin** (the gear icon), then under **Data collection and
   modification**, choose **Data streams**.
4. Open the web stream and confirm both identifiers:

   | Field | Value |
   |---|---|
   | Measurement ID | `G-9ZHLKD65GM` |
   | Stream ID | `16319805930` |
   | Website URL | `https://eitz-habina-prod.up.railway.app/` |

5. If the IDs do not match, stop and select the correct property/stream rather
   than creating another stream. You need the **Editor** or **Administrator**
   role on the property to change the settings below.

`https://eitz-habina-testing.streamlit.app/` is the testing site and is
permanently excluded by the app: it never loads the GA tag or sends events,
even with `admin=false`. Do not change the production stream's website URL to
the testing URL. The website URL is the production deployment address; it can
change later. See
[Changing the site URL](#5-changing-the-site-url) before changing domains.

## 2. Turn off enhanced measurement

1. In that web stream's details, find **Enhanced measurement**.
2. Turn the main **Enhanced measurement** switch **Off**.
3. Confirm that it remains off after leaving and reopening the stream.

This is important: the application already sends its own page views and
download events, and automatically collected site-search or navigation data
could expose unredacted query parameters. Turning off enhanced measurement
does not disable GA4's other automatically collected events. Do not add a
second Google tag, Google Tag Manager container, or other analytics integration
to the site; another integration could duplicate data or bypass the admin
opt-out. Review existing integrations separately if there are any.

## 3. Create the custom dimensions

Create the **17 event-scoped dimensions** in the table below. They make the
application's custom event parameters available in GA4 reports and
explorations. You can create them after the application has begun sending
events; if a parameter is not in the dropdown, type its exact name.

For **each row**:

1. Open **Admin** > **Data display** > **Custom definitions**.
2. Select **Custom dimensions**, then **Create custom dimension**.
3. Enter the **Dimension name** from the table.
4. Set **Scope** to **Event**.
5. Enter the exact **Event parameter** from the table, including underscores
   and lowercase letters. The dimension name is the readable report label; the
   event parameter is the exact code name.
6. Optionally paste the explanation into **Description**, then click **Save**.
7. Repeat for the next row. If a matching event-scoped definition already
   exists, use it rather than creating a duplicate.

The parameter and scope cannot be changed after saving, so double-check them.
Google's standard GA4 property limit is **50 event-scoped custom dimensions
per property**, including any already created. See **Quota information** on
the Custom definitions page. If you have fewer than 17 slots available, create
the **Core** rows first and add the **Detailed** rows as space permits.

| Priority | Dimension name | Scope | Event parameter | What it shows |
|---|---|---|---|---|
| Core | App language | Event | `app_language` | App UI language: `en` or `he`. |
| Core | Came from | Event | `came_from` | Previous page and control when known, or `entity_relationship_sources`. |
| Core | Search type | Event | `search_type` | `source`, `number`, `unit`, `entity`, or `tree`. |
| Core | Text similarity used | Event | `text_similarity_used` | `1` when a source search has text; `0` when it does not. |
| Core | Relationship filter used | Event | `relationship_filter_used` | `1` when a source search has a relationship filter; otherwise `0`. |
| Core | Passage types | Event | `passage_types` | Comma-separated source-search passage type names. |
| Core | Source types | Event | `source_types` | Comma-separated source-search source type names. |
| Core | Entity type | Event | `entity_type` | Type of one selected source-search entity or tree person. |
| Core | Entity ID | Event | `entity_id` | ID of one selected source-search entity or tree person. |
| Core | Entity name | Event | `entity_name` | English name of one selected source-search entity or tree person. |
| Core | Entity types | Event | `entity_types` | Entity types on a source search, or the entity-search page type. |
| Core | Entity IDs | Event | `entity_ids` | Selected source-search option IDs, or the entity-search ID. |
| Core | Entity names | Event | `entity_names` | Selected English names on a source search, or the entity-search name. |
| Detailed | Number value | Event | `number_value` | Searched number or fraction, for example `7` or `1/3`. |
| Detailed | Unit name | Event | `unit_name` | Validated English unit selected in number search. |
| Detailed | Tree type | Event | `tree_type` | `family_tree` or `studied_from`. |
| Detailed | Download type | Event | `download_type` | `source_results` for the source-results PDF button. |

`0` and `1` are categorical flags, so create **event-scoped dimensions**, not
custom metrics, for them. GA4 may parse numeric values on web events. Some
fields are absent when they do not apply or are empty, and GA4 can display
`(not set)` for those events. Individual entity IDs/names and combined lists can
have many distinct values; GA4 may group less frequent values into `(other)`.
The combined lists can also be truncated at 100 characters; use
`search_entity_filter` for individual selections.

### Do not create these definitions

- **`page_location`**: use GA4's existing **Page location** dimension. It is
  intentionally sanitized and is not the literal full search URL.
- **Event count** and **Event name**: use the built-in metric and dimension.
- **`search_id`**: it is a unique identifier joining a source search to its
  selected-entity events. Do not register it as a GA4 custom dimension: it
  would be high-cardinality. Use event-level export if you need that join.
- **`file_type`**: currently always `pdf` for the app's one download action;
  no custom dimension is needed to distinguish downloads.
- Do not create user-scoped or item-scoped dimensions, custom metrics, or
  key events for this setup. They are not required for these reports.

GA4 processes custom definitions asynchronously. Google says to allow
**24–48 hours** after the definition is created and data is sent before using
it in reports or explorations; do not assume past events will be backfilled.

## 4. Check collection and build reports

### Verify the integration

1. Confirm the application changes are deployed to the configured site.
2. Open `https://eitz-habina-prod.up.railway.app/?admin=false` in a fresh test tab.
   **This is a tracked visit** and will appear in the property's data. Do not
   use personal information in test searches.
3. Navigate from Home to another page, run a source search with a public test
   term and at least one entity filter, and click the PDF download button.
4. In GA4, open **Reports** > **Realtime**. Look for `page_view`, `app_search`,
   `search_entity_filter`, and `file_download`. Realtime can take a short time
   and may include other visitors. If the test browser uses ad blockers or
   prevents Google Analytics requests, events may not arrive.
5. To test exclusion, open `https://eitz-habina-prod.up.railway.app/?admin=true` in a
   **separate fresh tab**, navigate and reload. Check the browser's developer
   tools **Network** panel: that tab should not load `gtag/js` from
   `googletagmanager.com` or send Google Analytics collection requests. Filter
   the network log by `googletagmanager` and `collect` and clear it before the
   test. Realtime totals alone cannot prove exclusion when other people are
   using the site. `admin=false` explicitly re-enables tracking in that tab.
6. Confirm the testing-site exclusion separately at
   `https://eitz-habina-testing.streamlit.app/?admin=false`. Navigate and
   reload; the test tab should not load `gtag/js` or send GA collection
   requests. The testing site remains excluded even if `admin=false` is present.

No separate GA4 admin filter is required for the app's `admin=true` opt-out.
If another Google tag is installed outside this implementation, it must be
removed or independently excluded; this opt-out does not control it.

The testing origin is excluded in the app regardless of the `admin` query
parameter. If you have published a separate Google tag or analytics integration
directly on the testing deployment, remove it separately; the app's exclusion
controls only the app's GA4 component.

### Make a useful exploration

After the dimensions are available:

1. Open **Explore** > **Blank** (free-form exploration).
2. Under **Variables**, click **+** beside **Dimensions**, import **Event name**
   and the custom dimensions you want; click **Import**.
3. Click **+** beside **Metrics**, import **Event count**, then add **Event
   count** to **Values**.
4. Add dimensions to **Rows** and add a filter using **Event name**:

   | Question | Event name filter | Useful row dimensions |
   |---|---|---|
   | Which pages or controls lead to visits? | `page_view` | **Page location**, **Came from**, **App language** |
   | Which kinds of searches are used? | `app_search` | **Search type**, **App language** |
   | Are source searches using text or relationship filters? | `app_search` | **Search type**, **Text similarity used**, **Relationship filter used** |
   | Which individual entities are filtered in source searches? | `search_entity_filter` | **Entity type**, **Entity name**, **Entity ID**, **App language** |
   | Which entities are opened on Entity Search? | `app_search` | **Search type**, **Entity types**, **Entity names**, **Entity IDs**; filter **Search type** to `entity` |
   | How often is the PDF button clicked? | `file_download` | **Download type**, **App language** |

`search_entity_filter` fires once **per selected entity option**, not once per
search. Its event count is therefore a count of selected options, and should
not be added to `app_search` counts as another search. A PDF event records a
button click, not proof the file was saved.

## 5. Changing the site URL

1. Update the web stream's website URL in GA4 if appropriate.
2. Update the deployment's `EITZ_HABINA_BASE_URL` environment variable to the
   new origin, including scheme and any port, and redeploy/restart. Its default
   lives in `system_common/UrlPaths.py`. Set the Railway production deployment
   to `https://eitz-habina-prod.up.railway.app/`. The tracker only sends on that
   configured origin, except for the permanently excluded testing origin.
3. Repeat the verification above using the new URL, both with `admin=false` and
   in a fresh tab with `admin=true`.

The measurement ID remains `G-9ZHLKD65GM` unless you deliberately change
streams; if it changes, update the deployment's `GA4_MEASUREMENT_ID` too.

## References

- [Google: create event-scoped custom dimensions](https://support.google.com/analytics/answer/14239696?hl=en)
- [Google: enable or disable enhanced measurement](https://support.google.com/analytics/answer/9216061?hl=en)
- [Google: GA4 configuration limits](https://support.google.com/analytics/answer/12229528?hl=en)
- [Application event and privacy details](metrics.md)
