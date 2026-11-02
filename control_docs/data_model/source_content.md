# SourceContent

Source: `backend/models_db/SourceClasses/SourceContent.py`, `backend/db/mongo_parts/source_content_mixin.py`,
`backend_pipeline/data_pipeline/populator_scripts/DBPopulateSourceContent.py`.

One document per passage in the `TN` / `BT` collections (db `Sources`; see
`db_and_collections.md` for the key format).

## Structure

```
{ key: "BT_Bava Batra_0_16b:1-5", content: [ <EN html>, <HEB html> ] }
```

- `content` is exactly **2 strings**, indexed by `SourceContentType`: `EN = 0`, `HEB = 1`.
  Both are **raw HTML as fetched from Sefaria** (inline tags, `<i>` etc.).
- `SourceContentType.EN_CLEAN = 2` is **legacy**: clean English used to be stored as a 3rd
  element, but clean text is now computed on demand
  (`get_clean_en_text` / `get_clean_heb_text` via `miscFuncs`). Never write index 2.
  `DBPopulateSourceContent.DO_NOT_USE_populate_clean_english_content` is the dead writer.
- Validation (`is_valid_else_get_error_list`): list of strings, at least one non-empty.
  It does not enforce length 2.

## Cleanup

Leftover 3-element docs are trimmed by the one-time script
`backend_pipeline/data_pipeline/one_time_scripts/trim_source_content_to_en_heb.py`
(dry-run by default, `--apply` to write; runs `$slice: ["$content", 2]` on TN and BT,
skipping docs whose first two elements aren't strings). It writes to the real DB — see
`conventions/safety_and_testing.md`.

(The older `remove_third_content_element` query in `data_cleanup_mongo_queries.json` is
wrong: it concatenates the first 2 with the tail from index 3, i.e. it only removes index 2
and would keep any 4th+ element.)
