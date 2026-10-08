# Safety & Testing

## There is no separate test database

`DBParentClass.setUpClass` (`backend_pipeline/data_pipeline/DBScriptParentClass.py`) always
connects via `DBFactory.get_prod_db_mongo()`. Despite the name, this is simply the one
working MongoDB Atlas instance this project uses — there is no sandboxed test DB to fall
back on. **Every populator `test_*` method writes to real, persistent data.**

Rules of thumb:
- Never run a populator script that writes (anything beyond a `test_print_*`/report-only
  method) without the user's explicit go-ahead for that specific run.
- Read-only checks (a count query, `get_entities_by_display_en_name`, a dry-run report) are
  fine to run freely — they don't mutate anything.
- Destructive calls (`drop_all_entities`, `drop_all_rels`, bulk deletes) need extra-explicit
  confirmation — confirm scope (which collection(s)) before calling.

## Testing DB logic without touching real data

Use `mongomock` instead of a real connection:

```python
db = DBapiMongoDB()           # no connection_string -> __init__ skips connect()
db.client = mongomock.MongoClient()
db.dbs = {name: db.client[name] for name in {"Sources", "Graphs", "Faiss"}}
db.run_in_transaction = lambda callback: callback()   # mongomock has no real transactions
```

- `DBapiMongoDB` is a `@singleton` — this reconfigures the one process-wide instance, which
  is exactly what you want in a throwaway test script/process (never do this inside the
  actual running app).
- `run_in_transaction` faked as a plain passthrough is enough to validate *our* logic/shape
  (dedup, resolution, rel direction) — it does not exercise Mongo's own rollback semantics.
  For that, use a real throwaway single-node replica set instead (`mongod --replSet rs0
  --dbpath <tmp> --port 27999 --bind_ip 127.0.0.1`, then `replSetInitiate`, then
  `DBapiMongoDB("mongodb://127.0.0.1:27999/?directConnection=true")`).
- Install `mongomock` into a scratch `pip install --target <dir>` location, not the project
  venv (it's a test-only dependency, not a project dependency) — prepend that dir to
  `sys.path` in the throwaway script.
- Copy the real input JSON to a scratch path before running a populator against the fake DB,
  so any progress/idempotency file it writes doesn't land in the real project tree.

## Verifying a populator before a real run

1. Run its `test_print_*` / report-only method against the real DB (read-only) to confirm
   pre-flight checks pass and see the resolution/plan numbers.
2. Run the full mutating path once against a mongomock DB seeded with a copy of the real
   input, and spot-check a few non-trivial resolutions directly (by DB key, not just by name
   — two same-named entities make name-only checks misleading).
3. Run it a second time against the same mongomock DB and confirm entity/rel counts are
   unchanged (idempotency).
4. Only then run for real, after explicit approval.
