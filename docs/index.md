# Microsoft Foundry: End-to-End Workshop

> A **hands-on coding workshop** for building enterprise AI agents and apps on
> **Microsoft Foundry** (Azure AI Foundry).

Welcome! You'll go from your **first model call** to a **grounded, tool-using,
evaluated, observable agent** — and finish by combining it all into a capstone.
Every lab is a self-contained Jupyter notebook that also renders as a page on this
site, so you can read along or run it yourself against your own Foundry project.

!!! tip "One project, `az login`, and you're off"
    No hub-and-spoke Bicep, no APIM. The whole workshop runs against **one Foundry
    project** authenticated with **`DefaultAzureCredential`**. Start with
    **[Setup](setup.md)**.

---

## Read the platform primer first

Three short, code-free pages give you the mental model before lab 1:

| Page | What it covers |
|:--|:--|
| **[What is Foundry](platform/01-what-is-foundry.md)** | The unified PaaS, the two portals, what's built in. |
| **[Architecture & projects](platform/02-architecture-and-projects.md)** | Accounts, projects, connections, model deployments. |
| **[Control plane & governance](platform/03-control-plane-and-governance.md)** | Provisioning, regions, RBAC, gateways, Azure Policy. |

---

## The labs

Work through them in order — each builds on the last, and the client bootstrap from
M1 is reused everywhere.

| Module | You'll learn to… |
|:--|:--|
| **[M1 · First inference](modules/01-first-inference.ipynb)** | Call models with `AIProjectClient` — chat, embeddings, streaming, the Responses API. |
| **[M2 · Your first agent](modules/02-your-first-agent.ipynb)** | Create a versioned prompt agent and invoke it via `agent_reference`. |
| **[M3 · Tools & function calling](modules/03-tools-and-function-calling.ipynb)** | Attach the Code Interpreter and your own custom function tools. |
| **[M4 · Grounding / RAG (Foundry IQ)](modules/04-grounding-rag-foundry-iq.ipynb)** | Ingest a corpus into Azure AI Search and ground an agent with citations. |
| **[M5 · MCP tools](modules/05-mcp-tools.ipynb)** | Connect an agent to a Model Context Protocol tool catalog. |
| **[M6 · Agent memory](modules/06-agent-memory.ipynb)** | Give an agent cross-turn memory. |
| **[M7 · Multi-agent orchestration](modules/07-multi-agent-orchestration.ipynb)** | Route between specialist agents with the Agent Framework. |
| **[M8 · Deep research](modules/08-deep-research.ipynb)** | Run an agentic research loop with cited synthesis. |
| **[M9 · Evaluation](modules/09-evaluation.ipynb)** | Score quality with built-in, agent, and custom evaluators. |
| **[M10 · Observability & tracing](modules/10-observability-tracing.ipynb)** | Trace agents with OpenTelemetry → App Insights; evaluate continuously. |
| **[M11 · Guardrails](modules/11-guardrails.ipynb)** | Stack Prompt Shields, PII detection, and a custom blocklist. |
| **[M12 · Red teaming](modules/12-red-teaming.ipynb)** | Run automated adversarial scans against your agent. |
| **[M13 · Human-in-the-loop & REST](modules/13-human-in-the-loop-and-rest.ipynb)** | Pause for approval; invoke an agent over raw REST. |
| **[M14 · Fine-tuning](modules/14-fine-tuning-distillation.ipynb)** | Distill a teacher model into a small student (LoRA/PEFT). |
| **[M15 · Capstone](modules/15-capstone.ipynb)** | Combine everything into one agent — and where to go next. |

---

## Suggested agenda

This is comfortably a **two-day** workshop; compress to one long day by treating
M8 / M12 / M14 as "read & skim".

| Block | Modules |
|:--|:--|
| **Day 1 AM** — Foundations | Platform primer · M1 · M2 · M3 |
| **Day 1 PM** — Knowledge & tools | M4 · M5 · M6 · M7 |
| **Day 2 AM** — Quality & safety | M8 · M9 · M10 · M11 |
| **Day 2 PM** — Hardening & capstone | M12 · M13 · M14 · M15 |

---

## How to use this site

1. **Do [Setup](setup.md) first** — ~15 minutes, *before* the workshop.
2. **Read the [Concepts](concepts.md)** for the through-line that ties the labs together.
3. **Work the labs in order.** Each ends with a **🧪 Your turn** exercise.

!!! note "Run it yourself, anytime"
    Code cells render with an **"Expected output"** note in the surrounding text, so the
    site is useful even without Azure. To actually run a lab, use the **Download**
    link at the top of its page and point it at your own Foundry project.

Ready? → **[Set up your environment](setup.md)**
