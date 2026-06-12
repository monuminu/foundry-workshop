# Control plane & governance

> How you **operate** Foundry at scale — provisioning, regions, cost, RBAC,
> gateways, and policy. Conceptual background; **no code required** to do the labs.

The labs run against a single project you create by hand. In production, a platform
team operates a **fleet** of projects and agents. This page sketches that control plane
so the enterprise references in the labs make sense.

---

## 1. Provisioning

Enterprises provision Foundry with **infrastructure-as-code** (Bicep/Terraform) so the
topology is repeatable and reviewable. The reference series deploys, via Bicep:

- a **core gateway** account (shared models + an APIM front door),
- **project spokes** (1:1 per team, or 1:N multi-project),
- supporting resources: Azure AI Search, Application Insights, storage, ACR.

For the workshop you skip all of this — **portal click-ops to create one project +
deploy two models** is enough (see [Setup](../setup.md)).

---

## 2. Regions & model availability

Not every model is available in every region, and reasoning / deep-research models
often lead in a subset of regions. When you pick a region for your account, check that
your target models (e.g. `o3-deep-research`) are available there. The reference series
keeps region-availability notes per capability; for the labs, deploy in a region that
offers `gpt-4.1-mini` and `text-embedding-3-large` at minimum.

---

## 3. The AI gateway (APIM)

At scale, all model traffic is routed through an **AI gateway** — typically Azure API
Management — which provides:

- **per-team subscription keys** for independent rate limiting,
- **managed-identity backend auth** (no model keys in app code),
- a single **governed egress** point for logging and policy.

```
  team A ─┐
  team B ─┼─►  APIM gateway  ─►  model backends (regional)
  team C ─┘     (keys, quotas,        ▲
                 routing, logging)    └─ managed identity
```

!!! note "Why some labs note 'not supported through APIM'"
    When a project connects to models **via an APIM connection**, the supported call
    path is the **Responses API + agents**, not raw `chat.completions`. The workshop's
    direct single-project setup doesn't hit this constraint, but you'll see it called
    out because it matters in the enterprise topology.

---

## 4. Identity & RBAC

Auth across the platform is **`DefaultAzureCredential`** — your `az login` identity (or
a managed identity in production). **No admin keys in notebooks.** Access is granted at
the **project** scope via Azure RBAC roles, so onboarding a developer is one role
assignment, not a sprawl of per-resource grants.

```python
from azure.identity import DefaultAzureCredential
credential = DefaultAzureCredential()   # az login locally; managed identity in prod
```

---

## 5. Governance with Azure Policy

Because Foundry sits under **one resource provider**, Azure Policy can enforce
org-wide rules uniformly. A canonical example from the reference series:

> **Deny model deployments in project spokes** — forcing *all* inference through the
> core APIM gateway, so every request is logged, rate-limited, and policy-checked.

Other governance levers: **cost management** (per-project budgets and showback via the
gateway keys), **networking** (private endpoints), and **content safety** policies that
apply to every agent in scope.

---

## 6. Beyond the workshop

The control plane also covers operating concerns you'll meet in the capstone's
"where next":

- **Custom/registered agents** — register agents (even from other clouds) for unified
  fleet management in the **Operate** view.
- **Publishing** — surface agents in **Microsoft 365, Teams, and BizChat**.
- **Hosted agents** — containerized agent deployments (ACR-backed) for portability.
- **VS Code extension** — author and debug agents from your editor.

---

You now have the mental model for both the **single-project** path you'll code and the
**enterprise** path you'd grow into.

→ **[Set up your environment](../setup.md)** and start **[M1 · First inference](../modules/01-first-inference.ipynb)**.
