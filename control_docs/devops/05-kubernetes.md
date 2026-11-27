# Part 5 — Kubernetes on your own computer

[Contents](README.md) · **Prerequisites:** Part 3; Part 2 for the real app fixture ·
**Effort:** 1–2 days · **Cost:** local only

## The idea

Kubernetes is a **control plane** that reconciles declared desired state with actual
state. A **Pod** groups containers; a **Deployment** manages stateless Pods and
rollouts; a **Service** provides stable access to Pods; a **ConfigMap** holds
non-secret configuration. A Secret is a distribution mechanism, not automatically
safe encryption or a reason to commit credentials. Requests and limits shape
scheduling and resource use.

For a podcast: use the analogy of a controller repeatedly correcting a mismatch
between desired and actual state; explain why Kubernetes is useful at scale but
can add more operational burden than value to one Streamlit app.

## Local lab, not a production migration

1. Use [kind](https://kind.sigs.k8s.io/docs/user/quick-start/) and `kubectl` with a
   supported local container runtime. Name the lab cluster distinctly and confirm
   the active `kubectl` context before every mutating command. It uses local CPU,
   RAM and disk; there are no managed-cloud cluster fees.
2. Load the locally built image into kind and deploy one app replica in a dedicated
   namespace. Supply a fixture-only DB endpoint via config; use no production
   credentials. A local Compose service is not automatically reachable from a kind
   Pod: design and test network access, or run a disposable Mongo service inside
   the cluster. If Mongo is inside the cluster, protect it with scoped access and
   remember any in-cluster data is disposable for this exercise.
3. Expose the Service via local `kubectl port-forward` bound to loopback. Validate
   the Streamlit UI and WebSocket and a fixture-backed search; a running Pod alone
   isn't proof of application readiness.
4. Add carefully chosen startup/readiness/liveness checks. A process health endpoint
   is not a database or search check; don't make an external DB outage trigger an
   endless liveness restart loop. Measure model startup and memory before setting
   timeouts/limits. Inspect events and logs for a deliberately broken lab config.
5. Change an innocuous version label and observe rollout and rollback; delete one
   lab Pod and watch the controller replace it. Record the image and commit. Avoid
   a multi-replica Streamlit exercise until session/WebSocket routing, caches and
   DB connection load are understood; more replicas can use much more memory.
6. Optional: use Helm or Kustomize to compare environment overlays, and explain
   ConfigMaps, Secrets, namespaces and RBAC. Do not commit generated secrets or
   treat base64 encoding as encryption.

When finished, verify the name/context and delete **only** the named kind lab
cluster if desired. This deletes its cluster data; keep separately tested backups
where needed. No managed EKS/GKE, public load balancer, paid IP or cloud disk is
needed. Running Kubernetes locally teaches the API, not managed-cloud IAM,
autoscaling costs or production high availability.

## Done when

You can explain Pod/Deployment/Service and show a restart and rollback, access the
local app, and demonstrate a real isolated search. If data or model prerequisites are
missing, report the result as an orchestration-only demo.

**References:** [Kubernetes concepts](https://kubernetes.io/docs/concepts/);
[kind quick start](https://kind.sigs.k8s.io/docs/user/quick-start/);
[container plan](03-containers.md).

## Eitz Habina context for a standalone podcast

Eitz Habina, also called ChatBlatt, is a Torah-source research app where visitors
search Hebrew and English passages, explore people, places, numbers and
relationships, and follow tree views back to supporting sources. An offline pipeline
retrieves Sefaria passages and uses language-model-assisted extraction, validation
and review to prepare metadata. The live app reads those prepared results; metadata
may contain errors. The pipeline is background context, not the target of this lab.

The website is a Python Streamlit process with backend logic in the same app.
MongoDB's `Sources` stores passages, `Graphs` stores entities, relationships and
passage metadata, and `Faiss` stores FAISS semantic and BM25 keyword indexes.
The current corpus is Tanach and Babylonian Talmud, with Talmud Yerushalmi,
Midrash and Mishna planned. The user intends to retire Railway and keep the
Streamlit-hosted website. The existing Docker deployment can also run an optional
MCP server; it is not necessary for the local Kubernetes exercise. Kubernetes,
an isolated fixture database, and a Kubernetes-based production deployment are
not currently in place; this module proposes a local learning lab only.
