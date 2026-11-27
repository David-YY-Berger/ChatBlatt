# Part 7 — AWS, GCP, infrastructure as code and production choices

[Contents](README.md) · **Prerequisites:** none for study; Parts 1–3 for a real
deployment decision · **Effort:** 1–2 days for conceptual/local labs · **Cost:**
the default labs are $0; paid options below are clearly separate

## The idea

A cloud provider offers building blocks: compute, network, storage, identity and
managed databases. **IAM** answers who can do what; a **VPC** is a network boundary;
object storage, a persistent disk and a database have different access and
durability semantics. **Infrastructure as code (IaC)** records desired resources
in versioned configuration. OpenTofu's `plan` previews changes and `apply` changes
real infrastructure; its state may contain secrets.

For a podcast: compare a VM, managed container service and Kubernetes control
plane; compare AWS IAM/VPC/EC2/S3 with GCP IAM/VPC/Compute Engine/Cloud Storage.
Explain shared responsibility, least privilege, egress, storage, and why free quotas
are not the same as a permanently free production architecture.

## Labs that don't require a cloud bill

1. Draw the existing system: Streamlit hosting → TLS/network → MongoDB Atlas
   (`Sources`, `Graphs`, `Faiss`); users access Streamlit directly. Add MCP as a
   separate optional endpoint only if hosted. Mark secrets, read-only identities,
   indexes, backups and trust boundaries. Community Cloud's documented outbound IPs
   can change; design Atlas access rules accordingly without claiming IP allowlists
   replace authentication.
2. Map components to AWS and GCP service families on paper. Explain which components
   need a persistent home and which can be rebuilt. Estimate usage for an observed
   month: hours, GB stored, outbound GB, memory, requests, backups and monitoring.
   Compare against **current** pricing and region-specific quotas, including services
   outside free allowances. No cloud account is necessary.
3. Learn OpenTofu locally: inspect a small configuration targeting a disposable local
   Docker resource or use `tofu init -backend=false` and `tofu validate` for syntax
   and provider/schema validation only. Validation does not prove a cloud plan or
   deployability. A local provider lab may require downloads and a running runtime;
   use a dedicated lab directory and local state, not app/production resources.
   Review a plan before any apply; confirm the target is local. Never commit state,
   secrets or provider credentials. Back up or deliberately discard only lab state.
4. Optional local Linux/networking skill lab: inspect processes, ports, DNS, HTTP/TLS,
   environment variables, file permissions, logs and graceful termination. Practice
   with local services, not port scans of third-party systems.
5. For cloud-specific hands-on work, first verify an ongoing free allowance and a
   hard no-charge control that covers *all* resources and overages. If that cannot
   be established, stop at simulation/read-only documentation. No production data,
   cloud cluster, paid plan or temporary credit is required for this roadmap.

## Cost reality and possible future decisions

| Option | Role and tradeoff | Cost status |
|---|---|---|
| Streamlit Community Cloud + Atlas Free | Small public app; easy operations, separate providers, resource/availability limits and a 512 MB advertised Atlas storage limit | $0 only while eligible and within current terms/limits; measure actual fit |
| Local app + local Mongo | Learning, development, restore drills; not always-on public hosting | Software $0; your own hardware, network and electricity |
| Self-host on existing hardware | Possible public service only with networking, security, backups, uptime and power considerations | No hosting subscription, but not zero operating cost; don't expose a dev database |
| Managed cloud compute/database | Potentially less infrastructure maintenance, but memory, disk, requests, network, backup and availability all matter | Often chargeable; price using measured requirements first |
| Small paid VM with self-managed app and DB | Simple topology, but you own security, backups, patching and recovery; VM/disk/bandwidth are separate risks | **Later paid option**, not a recommendation or part of the $0 labs |
| Managed Kubernetes (EKS/GKE etc.) | Real managed orchestration experience; control plane, nodes and networking may cost | **Potentially paid**, avoid under the strict-free plan |

Neither AWS nor GCP credits are an always-free plan: AWS describes its new-account
Free plan as up to six months/credits, while GCP describes a 90-day trial. Some
services have ongoing allowances, usually with conditions and quotas; usage outside
them on billable accounts can cost money. A budget/alert is generally **not a hard
spending cap**; alerts can be delayed. Any service-specific spend cap must be checked
for coverage and eligibility. Do not enable billing or upgrade just to complete a lab.

For an eventual cheap production decision, first measure the expanded corpus, DB and
index sizes, RAM including model warm-up, concurrency, storage and transfer, then
compare full monthly cost, recovery and availability. Keep $0 and paid proposals
separate, include overage risks, and seek explicit approval before provisioning.
No provider can promise this app will remain both free and highly available as data
and usage grow.

## Done when

You can explain IAM, compute/network/storage, IaC plan/state and three deployment
tradeoffs; produce a cost worksheet from real measurements and official pricing;
and identify which activities are $0 local labs versus hypothetical chargeable
resources. No paid resources need to exist.

**References:** [AWS Free Tier](https://aws.amazon.com/free/);
[AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html);
[GCP Free Tier and trial](https://cloud.google.com/free/docs/free-cloud-features);
[GCP budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets);
[OpenTofu](https://opentofu.org/docs/intro/);
[Streamlit network limits](https://docs.streamlit.io/deploy/streamlit-community-cloud/status).

## Eitz Habina context for a standalone podcast

Eitz Habina, also called ChatBlatt, is a Torah-source research app. It lets people
search Hebrew and English passages, find entities and numbers, and explore
relationships and trees with supporting sources. A separate offline pipeline
retrieves Sefaria passages and uses language-model-assisted extraction, validation
and review to prepare metadata. The live site reads the prepared results, and
metadata may contain errors. Cloud exercises here concern the app, not rebuilding
the population pipeline.

The app is Python Streamlit with backend logic in the same process, reading three
logical MongoDB databases: `Sources` for passages, `Graphs` for entities,
relationships and passage metadata, and `Faiss` for FAISS semantic and BM25 keyword
indexes. The current populated corpus is Tanach and Babylonian Talmud; Talmud
Yerushalmi, Midrash and Mishna are planned. Their eventual size and traffic are
unknown, so no free hosting fit is guaranteed. The user intends to retire Railway
and keep the Streamlit website; the optional remote MCP server currently depends on
Railway. AWS, GCP, OpenTofu and other hosting choices in this module are learning
or future options, not infrastructure already deployed.
