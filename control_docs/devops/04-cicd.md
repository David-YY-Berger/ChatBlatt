# Part 4 — CI/CD and software supply chain

[Contents](README.md) · **Prerequisites:** none for offline CI; Parts 1–2 for
staging and promotion · **Effort:** 1–2 days · **Cost:** local or eligible free CI

## The idea

**Continuous integration** automatically checks a change; **continuous delivery**
keeps it releasable, often with manual promotion; **continuous deployment** releases
every passing change automatically. A green check only proves the checks that ran.
A build artifact should be traceable to a commit and its dependencies; rollback
redeploys an earlier compatible version rather than magically reverting data.

For a podcast: walk through a pull request, test isolation, artifacts, deployment
gates and the difference between CI passing and real-user availability.

## Start with the repository as it is

`.github/workflows/deploy.yml` currently runs `flyctl deploy --remote-only` on
pushes to `main` with a Fly token. Verify whether that workflow, token and Fly service
are actually active and billable. Don't confuse it with the existing Streamlit or
Railway deployments and don't run it during a learning lab. The app already has
`frontend/tests` unittest suites, Node tests for the metrics client, and a deployment
requirements file. Pipeline tests can write to the real DB, so never use indiscriminate
repository-wide discovery.

## Tasks

1. Create a test-only workflow for pull requests and selected branch pushes: check out
   code, select a supported Python, install app and explicitly declared test
   dependencies, and run a reviewed allowlist of offline frontend/backend tests.
   Include the existing Node metrics-client tests if Node is available. Confirm each
   selected test cannot reach or mutate production. Use a disposable service only
   after Part 2; no real credentials in the runner.
2. Add focused safety tests for configuration, fixture isolation, bilingual user
   journeys, source/number/entity/relationship search, and compatibility with new
   source types as those features are implemented. Keep fast mocked tests and a
   smaller real-Mongo integration layer distinct; mock databases do not prove Mongo
   transaction or permission semantics.
3. Add a container **build** check if useful. It should build but not publish or
   deploy. Consider dependency auditing and an SBOM (software bill of materials)
   as optional, reviewed tools; pin third-party Actions to reviewed full commit
   SHAs and minimize `GITHUB_TOKEN` permissions. Don't expose secrets to untrusted
   pull-request code or use privileged pull-request triggers to run it.
4. Show a deliberate broken test makes the check red, then fix it and see green.
   Observe runtime and logs; configure reasonable timeouts and concurrency so old
   superseded runs stop. Don't save dumps or credentials as CI artifacts.
5. Choose promotion: either manual deployment of a checked commit, or an automation
   that **actually enforces** passing checks before release. If Community Cloud
   watches `main` directly, merging can deploy regardless of a separate workflow
   unless repository protection and availability are verified. Test that behavior;
   a `workflow_run` or a green badge alone doesn't gate an independent deployment.
   For one developer, manual promotion can be simplest.
6. Before retiring a host, explicitly disable or remove stale deployment workflows
   and revoke their now-unused tokens after verifying they aren't used elsewhere.
   Document the tested commit, deployment result, smoke checks and rollback.

## Cost and security guardrails

GitHub says standard hosted runners for public repositories are free; private
repositories have included usage and may incur charges. Check current plan and
storage limits, avoid larger runners/paid services, set a restrictive spending
limit **where supported**, and use a local test command if a strict $0 limit cannot
be enforced. Limits, permissions and branch protection depend on plan and repository
visibility. A self-hosted runner uses your own machine and must not run untrusted
public PR code with access to local secrets or production.

## Done when

A reviewed test set runs without network access to production or production secrets,
an intentionally broken test fails CI, and a good commit passes. If doing delivery,
demonstrate that a failing check cannot reach production under the actual chosen
promotion mechanism, and rehearse rollback without writing the production DB.

**References:** [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions);
[secure workflow use](https://docs.github.com/en/actions/reference/security/secure-use);
[existing test commands](../frontend/metrics.md#verification).

## Eitz Habina context for a standalone podcast

Eitz Habina, also called ChatBlatt, is a Torah-source research app. Users search
Hebrew and English passages and explore people, places, numbers, relationships and
trees, with links to supporting passages. A separate offline pipeline collects
Sefaria passages and uses language-model-assisted extraction, validation and review
to prepare metadata; the website reads the results. Metadata may contain errors.

The Python Streamlit website calls backend code directly. MongoDB's `Sources` stores
passages, `Graphs` stores entities, relationships and passage metadata, and `Faiss`
stores semantic FAISS and keyword BM25 indexes. Tanach and Babylonian Talmud are
populated today; Talmud Yerushalmi, Midrash and Mishna are planned. The user intends
to remove Railway and retain the Streamlit website; a remote MCP endpoint is
optional and currently on Railway. There are existing app tests and a Fly deployment
workflow, but no separate test database: the Streamlit testing site shares the real
database. The CI checks and isolated staging described above are proposals, not
existing safeguards. Avoid accidentally running population tests that write real
data.
