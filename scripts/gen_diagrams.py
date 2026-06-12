#!/usr/bin/env python3
"""Generate workshop architecture diagrams as PNGs into docs/assets/.

Run from the repo root:
    PYTHONPATH=scripts python scripts/gen_diagrams.py

Produces clean, labeled diagrams in the MkDocs Material "indigo" palette:
    platform-overview.png      multi-agent-router.png
    inference-path.png         eval-observability.png
    agent-anatomy.png          rag-foundry-iq.png
"""
from __future__ import annotations

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ASSETS = pathlib.Path("docs/assets")
ASSETS.mkdir(parents=True, exist_ok=True)

# Material "indigo" palette + neutrals.
INDIGO = "#3f51b5"
INDIGO_DK = "#283593"
ACCENT = "#5c6bc0"
LIGHT = "#e8eaf6"
MINT = "#e0f2f1"
TEAL = "#00897b"
AMBER = "#ff8f00"
AMBER_BG = "#fff3e0"
GREY = "#546e7a"
GREY_BG = "#eceff1"
INK = "#1a237e"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
})


def _fig(w: float = 11, h: float = 6.2):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, *, fc=LIGHT, ec=INDIGO, tc=INK, fs=11,
        bold=False, rounded=0.02, lw=1.6):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.3,rounding_size={rounded*100}",
        linewidth=lw, edgecolor=ec, facecolor=fc, mutation_aspect=1,
    ))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, weight="bold" if bold else "normal",
            wrap=True)


def arrow(ax, x1, y1, x2, y2, *, color=INDIGO_DK, lw=2.0, style="-|>",
          ls="-", rad=0.0):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=18,
        linewidth=lw, color=color, linestyle=ls,
        connectionstyle=f"arc3,rad={rad}", shrinkA=2, shrinkB=2,
    ))


def title(ax, text, sub=None):
    ax.text(50, 96, text, ha="center", va="top", fontsize=16,
            weight="bold", color=INDIGO_DK)
    if sub:
        ax.text(50, 89.5, sub, ha="center", va="top", fontsize=10.5,
                color=GREY, style="italic")


def save(fig, name):
    out = ASSETS / name
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {out}")


# --------------------------------------------------------------------------- #
# 1. Platform overview — Foundry as a unified PaaS
# --------------------------------------------------------------------------- #
def platform_overview():
    fig, ax = _fig(11, 6.6)
    title(ax, "Microsoft Foundry — one unified platform",
          "Models, agents, knowledge, and tools behind a single RBAC / networking / policy surface")

    # Outer Foundry account boundary.
    ax.add_patch(FancyBboxPatch((4, 10), 92, 70,
                 boxstyle="round,pad=0.3,rounding_size=2.5",
                 linewidth=2.2, edgecolor=INDIGO, facecolor="#f5f6fb"))
    ax.text(8, 76, "Foundry account  ·  Project", fontsize=12, weight="bold",
            color=INDIGO_DK, ha="left")

    cards = [
        ("Models", "GPT-4.1 · o-series\nembeddings · OSS", LIGHT, INDIGO),
        ("Agents", "versioned\nprompt agents", MINT, TEAL),
        ("Knowledge", "Foundry IQ\nAzure AI Search", AMBER_BG, AMBER),
        ("Tools", "Code Interpreter\nMCP · functions", GREY_BG, GREY),
    ]
    x = 8
    for name, body, fc, ec in cards:
        box(ax, x, 46, 19, 22, "", fc=fc, ec=ec)
        ax.text(x + 9.5, 63.5, name, ha="center", fontsize=12.5, weight="bold",
                color=ec)
        ax.text(x + 9.5, 53.5, body, ha="center", va="center", fontsize=10,
                color=INK)
        x += 21.5

    # Cross-cutting platform services strip.
    box(ax, 8, 26, 84, 12,
        "Built-in:  tracing & observability  ·  evaluations  ·  guardrails  ·  red-teaming  ·  fine-tuning",
        fc="#ede7f6", ec=ACCENT, fs=10.2, bold=True)

    box(ax, 8, 13, 84, 8,
        "Control plane:  one RBAC · networking · Azure Policy · cost · single resource provider",
        fc=INDIGO, ec=INDIGO_DK, tc="white", fs=10.0, bold=True)

    save(fig, "platform-overview.png")


# --------------------------------------------------------------------------- #
# 2. Inference path — AIProjectClient -> OpenAI client -> APIs
# --------------------------------------------------------------------------- #
def inference_path():
    fig, ax = _fig(11, 5.6)
    title(ax, "The inference path",
          "One AIProjectClient gives you the OpenAI client and the agent surface")

    box(ax, 3, 52, 20, 20, "Your code\n\n az login →\nDefaultAzureCredential",
        fc=GREY_BG, ec=GREY, fs=10.5)
    box(ax, 29, 52, 21, 20, "AIProjectClient\n\nendpoint +\ncredential",
        fc=LIGHT, ec=INDIGO, fs=11, bold=True)
    box(ax, 56, 52, 21, 20, "openai_client\n\n.get_openai_client()",
        fc=MINT, ec=TEAL, fs=11, bold=True)

    arrow(ax, 23, 62, 29, 62)
    arrow(ax, 50, 62, 56, 62)

    # API surfaces fanned out from the openai client.
    apis = [
        ("chat.completions", "classic chat", 82, 70),
        ("embeddings", "vectors for RAG", 82, 56),
        ("responses", "Responses API\n+ agents + tools", 82, 40),
    ]
    for name, body, x, y in apis:
        box(ax, x, y - 5, 16, 11, f"{name}\n{body}", fc="#f5f6fb",
            ec=ACCENT, fs=9.5)
        arrow(ax, 77, 62, x, y, rad=-0.15 if y > 60 else (0.0 if y == 56 else 0.18))

    box(ax, 29, 20, 48, 16,
        "Models are deployed in the project (or served via a gateway).\n"
        "Pick the deployment by name:  CHAT_MODEL = \"gpt-4.1-mini\"",
        fc=AMBER_BG, ec=AMBER, fs=10.5)
    arrow(ax, 39, 52, 39, 36, color=AMBER, ls="--")
    arrow(ax, 66, 52, 66, 36, color=AMBER, ls="--")

    save(fig, "inference-path.png")


# --------------------------------------------------------------------------- #
# 3. Agent anatomy — definition + Responses API + tools
# --------------------------------------------------------------------------- #
def agent_anatomy():
    fig, ax = _fig(11, 6.2)
    title(ax, "Anatomy of a Foundry agent",
          "A versioned definition, invoked through the Responses API, calling tools in a loop")

    box(ax, 4, 58, 26, 22,
        "PromptAgentDefinition\n\nmodel\ninstructions\ntools",
        fc=LIGHT, ec=INDIGO, fs=10.5, bold=True)
    ax.text(17, 53, "agents.create_version(...)", ha="center", fontsize=9.5,
            color=GREY, style="italic")

    box(ax, 38, 60, 24, 18, "Responses API\n\nresponses.create(\n  agent_reference )",
        fc=MINT, ec=TEAL, fs=10.5, bold=True)

    box(ax, 70, 70, 26, 11, "Model\nreason / plan", fc="#f5f6fb", ec=ACCENT, fs=10.5)
    box(ax, 70, 53, 26, 12, "Tools\nCode Interpreter ·\nfunctions · MCP", fc=AMBER_BG,
        ec=AMBER, fs=10.0)

    arrow(ax, 30, 69, 38, 69)
    arrow(ax, 62, 71, 70, 75)            # to model
    arrow(ax, 62, 67, 70, 59)            # to tools
    arrow(ax, 70, 56, 62, 64, rad=0.25, color=AMBER)   # tool result back
    ax.text(67, 50.5, "tool result loops back", fontsize=9, color=AMBER,
            ha="center", style="italic")

    box(ax, 38, 30, 24, 14, "output_text\n\nfinal answer", fc=GREY_BG, ec=GREY,
        fs=10.5, bold=True)
    arrow(ax, 50, 60, 50, 44)

    box(ax, 4, 12, 92, 12,
        "Versioning:  every create_version bumps the agent so you can iterate on instructions/tools\n"
        "and roll back — the agent name stays stable, the behaviour is tracked.",
        fc="#ede7f6", ec=ACCENT, fs=10.2)

    save(fig, "agent-anatomy.png")


# --------------------------------------------------------------------------- #
# 4. RAG / Foundry IQ flow
# --------------------------------------------------------------------------- #
def rag_foundry_iq():
    fig, ax = _fig(11, 5.8)
    title(ax, "Grounding with Foundry IQ (RAG)",
          "Ingest → embed → index → build a knowledge base → ground an agent")

    steps = [
        ("Documents", "your corpus", GREY_BG, GREY),
        ("Embed", "embeddings\nmodel", LIGHT, INDIGO),
        ("Azure AI\nSearch index", "vector + text", MINT, TEAL),
        ("Knowledge\nbase", "Foundry IQ", AMBER_BG, AMBER),
    ]
    x = 3
    for name, body, fc, ec in steps:
        box(ax, x, 56, 19, 18, f"{name}\n\n{body}", fc=fc, ec=ec, fs=10.2, bold=True)
        if x > 3:
            arrow(ax, x - 2.5, 65, x, 65)
        x += 22

    # Agent grounded on the KB.
    box(ax, 30, 24, 26, 16, "Agent\n\ngrounded answers\nwith citations",
        fc=LIGHT, ec=INDIGO, fs=10.5, bold=True)
    arrow(ax, 75, 56, 50, 40, color=AMBER, rad=0.2)
    ax.text(70, 47, "retrieve", fontsize=9.5, color=AMBER, style="italic")

    box(ax, 64, 26, 30, 13, "User question\n→ retrieve → cite → answer",
        fc="#f5f6fb", ec=ACCENT, fs=10.0)
    arrow(ax, 64, 32, 56, 32)

    save(fig, "rag-foundry-iq.png")


# --------------------------------------------------------------------------- #
# 5. Multi-agent router + specialists
# --------------------------------------------------------------------------- #
def multi_agent_router():
    fig, ax = _fig(11, 6.0)
    title(ax, "Multi-agent: router + specialists",
          "A router classifies intent and dispatches to a domain specialist (Agent Framework WorkflowBuilder)")

    box(ax, 6, 52, 22, 16, "User request", fc=GREY_BG, ec=GREY, fs=11, bold=True)
    box(ax, 38, 52, 24, 16, "Router agent\n\nclassify intent", fc=INDIGO,
        ec=INDIGO_DK, tc="white", fs=11, bold=True)
    arrow(ax, 28, 60, 38, 60)

    specialists = [
        ("HR agent", "HR KB", 74, 74),
        ("Marketing agent", "Marketing KB", 74, 54),
        ("Products agent", "Products KB", 74, 34),
    ]
    for name, body, x, y in specialists:
        box(ax, x, y - 6, 22, 13, f"{name}\n{body}", fc=MINT, ec=TEAL, fs=10.2,
            bold=True)
        arrow(ax, 62, 60, x, y, rad=-0.18 if y > 60 else (0.0 if y == 54 else 0.18))

    box(ax, 30, 12, 40, 12,
        "WorkflowBuilder wires router → specialists as a graph;\n"
        "each specialist is grounded on its own knowledge base.",
        fc="#ede7f6", ec=ACCENT, fs=10.0)

    save(fig, "multi-agent-router.png")


# --------------------------------------------------------------------------- #
# 6. Evaluation + observability loop
# --------------------------------------------------------------------------- #
def eval_observability():
    fig, ax = _fig(11, 6.0)
    title(ax, "Quality loop: evaluate offline, observe in production")

    # Offline eval (left).
    box(ax, 4, 74, 40, 9, "OFFLINE — before you ship", fc=INDIGO, ec=INDIGO_DK,
        tc="white", fs=10.5, bold=True)
    box(ax, 4, 56, 18, 13, "Test set\njsonl", fc=GREY_BG, ec=GREY, fs=10)
    box(ax, 26, 56, 18, 13, "Evaluators\nquality · agent ·\ncustom", fc=LIGHT,
        ec=INDIGO, fs=9.8, bold=True)
    arrow(ax, 22, 62.5, 26, 62.5)
    box(ax, 13, 38, 22, 12, "Scores\ngroundedness,\nrelevance, safety", fc=MINT,
        ec=TEAL, fs=9.8)
    arrow(ax, 35, 56, 24, 50, rad=0.1)

    # Production obs (right).
    box(ax, 56, 74, 40, 9, "ONLINE — in production", fc=TEAL, ec="#00695c",
        tc="white", fs=10.5, bold=True)
    box(ax, 56, 56, 18, 13, "Agent run\nlive traffic", fc=LIGHT, ec=INDIGO, fs=10)
    box(ax, 78, 56, 18, 13, "OpenTelemetry\n→ App Insights", fc=AMBER_BG, ec=AMBER,
        fs=9.8, bold=True)
    arrow(ax, 74, 62.5, 78, 62.5)
    box(ax, 67, 38, 22, 12, "Continuous\nevaluation +\nalerts", fc="#ede7f6",
        ec=ACCENT, fs=9.8)
    arrow(ax, 87, 56, 78, 50, rad=0.1)

    # Feedback into a shared "iterate" box — arrows land on the box top edge,
    # left and right of the centered label so they never cross the text.
    box(ax, 20, 13, 62, 11,
        "Findings feed back into instructions, tools, and the test set  →  iterate",
        fc="#f5f6fb", ec=ACCENT, fs=10.5, bold=True)
    arrow(ax, 24, 38, 31, 24.3, color=GREY, rad=0.12)
    arrow(ax, 78, 38, 71, 24.3, color=GREY, rad=-0.12)

    save(fig, "eval-observability.png")


if __name__ == "__main__":
    platform_overview()
    inference_path()
    agent_anatomy()
    rag_foundry_iq()
    multi_agent_router()
    eval_observability()
    print("\nAll diagrams written to docs/assets/")
