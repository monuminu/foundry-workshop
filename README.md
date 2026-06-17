# Microsoft Foundry: End-to-End Workshop

A hands-on, end-to-end coding workshop for building enterprise AI agents and apps
on **Microsoft Foundry (Azure AI Foundry)** — Azure's unified PaaS for models,
agents, knowledge, evaluation, and observability.

📖 **Read the workshop online:** <https://monuminu.github.io/foundry-workshop/>

The workshop is a MkDocs site whose lab pages are runnable Jupyter notebooks.
Read it on the web, or clone this repo and run every lab against your own Foundry
project.

## What you'll build

Starting from a single Foundry project and `az login`, you progress from your first
model call to a grounded, tool-using, evaluated, observable agent:

1. **First inference** — chat, embeddings, streaming, the Responses API
2. **Your first agent** — versioned prompt agents
3. **Tools & function calling** — Code Interpreter + custom tools
4. **Grounding / RAG** — Azure AI Search knowledge bases (Foundry IQ)
5. **MCP tools** — connect an agent to a Model Context Protocol server
   - **Work IQ** — ground an agent in live, permission-aware Microsoft 365 work context (M5b)
6. **Agent memory** — cross-turn context
7. **Multi-agent orchestration** — router + specialists
8. **Deep research** — agentic research loops with cited synthesis
9. **Evaluation** — quality, agent, and custom evaluators
10. **Observability** — OpenTelemetry tracing + continuous evaluation
11. **Guardrails** — Prompt Shields, PII, custom blocklists
12. **Red teaming** — automated adversarial scans
13. **Human-in-the-loop & REST** — approvals + raw REST invocation
14. **Fine-tuning** — knowledge distillation to a small model
15. **Capstone** — combine it all, plus where to go next

## Quick start

```bash
git clone https://github.com/monuminu/foundry-workshop.git
cd foundry-workshop

# Author/build the site + run notebooks locally
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[docs]"

# Preview the site
mkdocs serve        # http://127.0.0.1:8000
```

To **run the labs** against Azure you'll also need `pip install -e .`, an `az login`,
and a Foundry project with deployed models. See **[Setup](docs/setup.md)** for the
full prerequisites and environment variables.

## Authoring

Lab notebooks are generated programmatically — never hand-edited as JSON. Each
module has a generator under `scripts/gen_<id>.py` that builds its notebook via
`scripts/nbbuild.py`. To regenerate:

```bash
PYTHONPATH=scripts python scripts/gen_01_first_inference.py
python scripts/check_notebook_links.py docs/modules   # in-notebook link safety
mkdocs build --strict                                  # whole-site build
```

## License

MIT
