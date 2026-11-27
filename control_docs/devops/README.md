# DevOps learning roadmap for ChatBlatt

This is a **plan, not implemented infrastructure**. Pick individual modules or follow
the suggested path; you do not need Kubernetes, AWS, or a pipeline redesign to make the
Streamlit app safer. Exercises focus on the app, not data population. Any future database
population or restore is a separate, explicitly authorized operation.

## Table of contents

| Part | Focus | Minimum prerequisite | Outcome |
|---|---|---|---|
| [1. Environments and release basics](01-environments.md) | Dev, test, staging, production; Railway retirement | None | A safe release boundary and concrete cutover checklist |
| [2. Database isolation and recovery](02-database.md) | Separate DB targets, fixtures, backup and restore | None for design; Part 1 for deployed staging | Tests cannot accidentally write to production; a practiced recovery |
| [3. Docker and local Compose](03-containers.md) | Images, containers, local networking and volumes | None; Part 2 for a working isolated DB | Run the app and a disposable database locally |
| [4. CI/CD and supply chain](04-cicd.md) | Automated tests, build, promotion, rollback | None for CI; Parts 1–2 for safe staging promotion | Repeatable checks without production credentials |
| [5. Kubernetes, locally](05-kubernetes.md) | Pods, deployments, services, configuration | Part 3; Part 2 for real app data | A local learning cluster, not a production requirement |
| [6. Observability and operations](06-observability.md) | Logs, health, capacity, incidents | None; Parts 1–2 for environment-specific checks | Detect problems and practice recovery |
| [7. Cloud, infrastructure as code, production choices](07-cloud-production.md) | AWS/GCP concepts, OpenTofu, free/cheap hosting | None for study; Parts 1–3 for deployment decisions | An evidence-based hosting decision without surprise bills |

**Suggested order:** 1 → 2 → 4, then 3 → 5. Do 6 alongside them and 7 whenever
interested. A smaller first slice is 1 + 2 + the test-only portion of 4. A module
marked as dependent on another can still be read independently.

## Current starting point

- **What Eitz Habina does:** Eitz Habina, also called ChatBlatt, is a research app
  for exploring Torah sources. It presents passages in English and Hebrew and lets
  people search for sources, people, places, numbers, and relationships. Tree
  views help users explore connections between entities and follow them back to
  supporting passages.
- **How its information is prepared:** An offline population pipeline retrieves
  passages from Sefaria and uses language-model-assisted extraction, validation and
  human review to produce entity and relationship metadata. It builds search
  indexes separately. The live app reads the resulting data; it does not need
  the population pipeline to run for each visitor. Metadata may contain errors,
  even though the app links back to source passages.
- The app is a Python Streamlit process, launched from `streamlit_app.py`, calling
  backend logic directly; it is not a separate web API and does not require Railway.
- `Sources`, `Graphs`, and `Faiss` are three **logical MongoDB databases on one
  deployment**, not three independent servers. `Faiss` contains both FAISS and BM25
  GridFS data. Current source data is Tanach and Babylonian Talmud; later additions
  change capacity, compatibility, and search testing requirements.
- A Streamlit testing site exists and suppresses analytics, but it does not have a
  separate database. A different hostname or `admin=true` is not database isolation
  or access control.
- `DBFactory` hardcodes the Atlas host; app calls use `get_prod_db_mongo()` and a
  process-wide `DBapiMongoDB` singleton. Simply supplying different credentials or
  a different site URL does not select a different database server.
- The repository already has a Dockerfile for Railway's nginx + Streamlit + optional
  MCP setup, frontend unit tests, and a GitHub Actions workflow that attempts to deploy
  to Fly on pushes to `main`. That workflow is not an app test workflow. Check its
  actual enablement and billing before changing it.
- The Streamlit site can remain public while Railway is removed, but the currently
  documented remote MCP endpoint is hosted on Railway. Removing Railway removes that
  endpoint unless it is separately replaced.

For podcast generation: the app's website, backend logic, database and search indexes
are the focus of the DevOps exercises. The pipeline is background context, not a
proposed DevOps project. Each of the seven parts repeats the essential app context
so it can be understood independently. Statements about future infrastructure are
proposals, not descriptions of features that already exist.

See [program overview](../program_overview.md), [frontend overview](../frontend/overview.md),
[database model](../data_model/db_and_collections.md), and
[database safety](../conventions/safety_and_testing.md) for the existing behavior.

## The zero-cost contract

Core labs use local software and existing free services, with **no trial credits and
no paid-plan upgrade required**. Local computing still uses your own hardware,
electricity, and internet; no outside provider promises unlimited resources or
unchanged free terms for years. Read the current terms before signing up, installing,
or deploying. Stop if a step requires a paid account, a trial, or a potentially
chargeable resource; use the local or paper alternative instead. In particular:

- Streamlit Community Cloud and Atlas Free are possible $0 hosting components, **not
  guarantees** that the growing dataset or workload fits, or that the app is always
  available. Atlas currently advertises 512 MB per free cluster; measure actual
  logical/storage usage and provider-enforced limits rather than assuming it fits.
- GitHub Actions standard hosted runners are free for public repositories; private
  repositories have included limits and potential charges. Artifacts, packages,
  large runners and other services have their own rules. A local runner or no CI is
  the fallback.
- AWS and GCP have some ongoing free allowances, but new-account credits are
  **temporary**, paid billing can allow overages, and budget alerts are not a
  universal spending cap. The default cloud exercises are local or conceptual.
- The explicitly labeled **later paid options** in Part 7 are comparisons only,
  not part of the free learning plan. No automatic provisioning or paid deployment
  is authorized by this roadmap.

Pricing and limits checked against linked provider pages on 27 November 2026; verify
again before every real deployment. Free-tier eligibility, available regions, usage
and billing behavior can change.

## How to use each module

Each has concepts for a future podcast, concrete choices and exercises, a safety/cost
boundary, and a measurable definition of done. Estimates are rough learning time,
not deadlines. Suggested implementation paths are candidates, not promises that files
already exist. Keep this roadmap separate from live operational facts; update the
existing architecture and safety docs when implementation actually changes them.
