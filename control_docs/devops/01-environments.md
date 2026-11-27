# Part 1 — Environments and release basics

[Contents](README.md) · **Prerequisites:** none · **Effort:** 3–6 hours for
design and a first release checklist; implementation is separate · **Cost:** $0

## The idea

An **environment** is an independently configured combination of code, data, secrets,
permissions, and runtime. A branch is only a version of code; it is not an isolated
environment. **Development** is your workstation, **test** is disposable and
repeatable, **staging** approximates production for a final check, and **production**
serves real users. The same code should behave according to explicit configuration,
not a secret branch-specific edit.

For a podcast: explain the difference between a deployment and a release, why
“staging URL” alone is not staging isolation, and how promoting the same Git commit
reduces “works on my machine” surprises.

## Current facts and desired target

| Environment | Compute | Database | Secrets and analytics |
|---|---|---|---|
| Local development | Windows/WSL, optionally container | Local, non-production Mongo | Local-only credentials; no production analytics |
| Automated test | Local or CI process | Synthetic fixture or disposable Mongo | No real app credentials or real user telemetry |
| Staging, optional | Existing Streamlit testing site or local | Separate staging deployment or synthetic fixture | Distinct read-only credentials; analytics disabled |
| Production | Streamlit Community Cloud | Explicitly selected production Mongo | Production read-only credential; own base URL/analytics |

Today the testing site is a separate UI deployment but shares the real Mongo target.
Its banner and analytics opt-out are useful, not safety boundaries. A local staging
environment is a legitimate $0 option if a second hosted database is not feasible;
it cannot validate the hosted provider's network, secrets, or runtime.

## Tasks and choices

1. Inventory, without printing secret values: deployment URLs, branch/commit, hosting
   settings, secret **names**, DB targets and roles, `EITZ_HABINA_BASE_URL`, external
   links, and rollback owner. Record which settings are unknown and verify them.
2. Choose a simple promotion model. Example: feature branch → tested `main` for
   production; a separate staging branch deployed to the testing site. Agree which
   commit moves between them. Streamlit can redeploy on branch changes, so confirm
   actual branch settings: merging to an auto-deployed production branch **is** a
   release. Avoid claiming a CI gate unless deployment really waits for it.
3. Design a required, validated environment setting and explicit Mongo connection
   selection. Missing or unknown settings should fail clearly, never silently select
   production. Keep separate secrets on each deployment. Part 2 covers the singleton,
   authentication, and preventing wrong-target writes.
4. Configure the correct base URL for each deployment; verify shareable links,
   browser analytics and testing-site suppression. A URL flag is not an auth system.
5. Document a release: record the tested commit, validate staging, promote, verify
   the production commit and key user journeys, and document who can approve a
   database change. Rollback means redeploying a known-good commit **and** confirming
   it is compatible with the current data; it does not undo database changes.

## Before taking Railway down

- Confirm Community Cloud runs `streamlit_app.py` with the intended branch, Python,
  secrets and production **read-only** DB role. Verify its URL configuration and
  analytics behavior. Check source search, Hebrew and English, entity and number
  search, a tree, shared links, PDF, and mobile navigation.
- The default in `system_common/UrlPaths.py` and the MCP setup page currently refer
  to Railway. Plan code/docs updates so links don't send users to a removed site.
  Update both language strings if the UI message changes; check metrics and MCP docs.
- Decide explicitly whether to remove/mark the MCP setup as unavailable or host MCP
  separately. Community Cloud running the standalone entrypoint does not itself
  expose Railway's `/mcp`. Test the chosen UX after cutover.
- Inventory DNS, links, access credentials and the Fly workflow. Disable or remove
  deployment automation only after confirming what is actually active; rotate/revoke
  unused tokens and credentials when no longer needed. Keep a rollback decision
  and read-only backup before retiring anything.

## Done when

You can identify the code commit, database target, privilege level and analytics
setting of each environment without revealing secrets; a release and compatible
rollback are documented and rehearsed. Until Part 2 is complete, label hosted
testing as **not data-isolated**. When Railway is retired, check the actual public
site and MCP messaging rather than treating this checklist as proof.

**References:** [Streamlit deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app);
[existing frontend configuration](../frontend/overview.md);
[metrics](../frontend/metrics.md); [MCP deployment](../app/mcp.md).

## Eitz Habina context for a standalone podcast

Eitz Habina, also called ChatBlatt, is a Torah-source research app. Visitors can
explore Hebrew and English passages, search for people, places and numbers, and
view relationships and trees with links back to sources. An offline pipeline uses
Sefaria passages and language-model-assisted extraction, validation and review to
prepare the data; the website reads the prepared data rather than running that
pipeline for every request. Its metadata can contain errors.

The website is a Python Streamlit app whose backend logic reads MongoDB: `Sources`
holds passages, `Graphs` holds entities, relationships and passage metadata, and
`Faiss` holds semantic and keyword search indexes. The populated corpus is currently
Tanach and Babylonian Talmud; Talmud Yerushalmi, Midrash and Mishna are planned.
The user intends to retire Railway and retain the Streamlit website. The existing
Streamlit testing site is a separate website deployment but currently points to the
same database as production; an isolated database and release process are goals,
not existing features. The remote MCP server is optional and currently tied to
Railway.
