# Part 3 — Docker and local Compose

[Contents](README.md) · **Prerequisites:** none for the image lab; Part 2 for a
fixture-backed DB · **Effort:** 4–8 hours · **Cost:** local only

## The idea

An **image** is a versioned filesystem and startup recipe; a **container** is a
running instance of it. A Dockerfile builds an image in layers. Compose describes
multiple local containers and their network. A **volume** survives a container
restart, whereas the container filesystem should be considered disposable. None of
these is itself a backup. Linux containers on Windows typically use WSL 2.

For a podcast: explain image vs container vs volume, port publishing versus
container-to-container DNS, and why pinning dependencies and minimizing image
contents help reproduce a deployment.

## Build on the existing app

The existing root `Dockerfile` builds a Python virtual environment and runs
`deploy/start.sh`: nginx, Streamlit, and optionally MCP. It is designed for the
Railway-style combined deployment; `MCP_ENABLED=false` still starts nginx. Streamlit
Community Cloud uses `streamlit_app.py` directly and does not build this Dockerfile.
The deployment requirements include `sentence-transformers`, FAISS and other
substantial dependencies, so build size, model downloads, memory and cold starts
must be measured, not assumed small.

## Labs

1. Review the existing Dockerfile, start script and nginx proxy; draw the processes
   and ports. Build locally and inspect image size and layers. Use personal-use
   Docker Desktop if its current license applies, or another compatible free
   container runtime; see [Docker Desktop license](https://docs.docker.com/subscription-billing/desktop-license/).
2. Decide whether to retain the combined image for a lesson or add a lean
   Streamlit-only local image/target. Do not break the existing entrypoint silently.
   Exclude `.env`, secrets, backups, virtual environments and generated data via
   an audited build context/`.dockerignore`. Never bake credentials into an image.
3. Run a local container with non-production configuration and explicitly published
   loopback port. Pass secrets via an untracked local mechanism, not image build
   arguments, committed Compose files, terminal transcripts or logs. Container
   environment values can still be inspected by local administrators.
4. Optionally add a Compose file with app + Mongo and a **named local development
   volume**, plus the synthetic fixture from Part 2. Inside the app container,
   `localhost` means the app container, not the database container: use the Compose
   service name. Adapt target config rather than assuming the hardcoded Atlas URI
   works. Restrict any published database port to loopback; configure authentication
   or keep the disposable DB inaccessible beyond the local network.
5. Verify readiness, not just container existence: inspect logs without credentials,
   open Streamlit, run a real fixture-backed search, restart the app and demonstrate
   volume persistence. Observe that startup ordering alone does not ensure DB
   readiness. Define and test graceful failure/retry behavior.
6. As an experiment, stop and remove only this lab's named containers; retain its
   volume unless you explicitly intend to destroy the disposable data. Verify any
   volume's identity before removal. Never point a destructive exercise at production.

**Optional:** compare container process memory with and without similarity search,
and compare a Streamlit-only process with the two-process MCP configuration. Measure
after a representative query; cold import is not peak usage.

## Done when

A fresh local image runs the actual app against a verified non-production fixture,
search works, secrets aren't in the image/build context, and you can explain what
survives a restart. If the fixture is not ready, document the build/start lab as
partial rather than claiming end-to-end success.

**References:** [Docker concepts](https://docs.docker.com/get-started/docker-concepts/);
[Compose](https://docs.docker.com/compose/); [current frontend deployment](../frontend/overview.md).

## Eitz Habina context for a standalone podcast

Eitz Habina, also called ChatBlatt, helps people research Torah sources through
Hebrew and English passage search, entity and number searches, and relationship
trees that link back to supporting sources. An offline pipeline gets passages from
Sefaria and uses language-model-assisted extraction, validation and review to
prepare metadata. The online app reads that prepared data; metadata can contain
errors and the population pipeline is not the focus of this plan.

The online app is Python and Streamlit, with backend logic in the same application
process. MongoDB stores passages in `Sources`, entities and relationships in
`Graphs`, and FAISS semantic and BM25 keyword search indexes in `Faiss`. Tanach and
Babylonian Talmud are currently populated; Talmud Yerushalmi, Midrash and Mishna
are planned. The user intends to retire Railway and keep the Streamlit-hosted site.
The existing Docker image starts Streamlit and nginx, with an optional separate MCP
process; Community Cloud runs the Streamlit entrypoint directly. A local
fixture-backed container setup described above is a learning goal, not an already
isolated test environment.
