# Number search

Source: `frontend/pages/number_search.py`.

Flow: `NumberSearchController` → `NumberSearchLogic.execute` (backend) returns
`NumberSearchResult.by_category` (`NumberCategory | None` → list of `NumberOccurrenceDTO`, one
per context × source). Entity model: `data_model/entities/number.md`.

- **Input**: one free-form box (Enter or Search button). Whole vs. fraction auto-detected;
  `_validate_number` gives live error messages (rejects 0/1, decimals, negatives).
- **Results**: big number header → coloured category tabs (with counts) → per-tab unit filter
  → table.
- **Results list**: organised by **unit** (`_group_by_unit`). Every unit is a collapsed card showing a chevron, the unit name and a source-count badge. Opening a card reveals one row per source: Context(s) (all contexts of that unit in that source, merged), Source Summary, and Source (click opens the source popup, positioned near the click; see `components/source_popup.py` `spOpen`). Rendered as static HTML in an iframe; expand/collapse is inline JS that also resizes the iframe (`window.frameElement`).
