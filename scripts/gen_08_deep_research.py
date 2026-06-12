"""Generate Module 8 — Deep Research.

Distilled from the upstream reference 12-foundry-iq-deep-research
(12-02-deep-research-loop.ipynb; 12-01 deploys the o3 backend — skipped here),
simplified to a single Foundry project + DefaultAzureCredential.

The reference runs two AzureOpenAI clients through an APIM gateway (a research
client for `o3-deep-research` in a separate region, a synthesis client for
`gpt-4.1-mini`) and grounds the loop on a Foundry IQ knowledge base
(`arxiv-nlp-kb`) reached via the Search `retrieve` REST API. We strip all of
that: one `get_openai_client()` serves BOTH model deployments (research +
synthesis), and the "knowledge source" is a tiny in-notebook corpus so the lab
is self-contained and the lesson stays on the **agentic deep-research loop** —
plan, search/fetch, iterate, synthesise a cited report. A note shows how to swap
the corpus for a real Foundry IQ KB (M4) in production.

RESEARCH_MODEL is read from .env (default `o3-deep-research`).
"""
from nbbuild import md, code, write_notebook, next_link, sibling_link, page_link

KERNEL = "foundry-workshop"
KERNEL_DISPLAY = "Microsoft Foundry: End-to-End Workshop"

cells = [
    md("""\
# M8 · Deep Research

> **Goal:** run an **agentic research loop** — a reasoning model that plans, searches a knowledge source, iterates, and returns a **cited synthesis**.
> **You'll use:** `o3-deep-research` over `chat.completions` with function tools, plus a chat model for the final report.

---

A normal chat answer is one shot. **Deep research** is different: you pose a hard question,
and a **reasoning model** (`o3-deep-research`) plans an investigation — it decides what to
**search**, reads what it **fetches**, searches again to fill gaps, and only then concludes.
A second, cheaper model turns those findings into a clean, **cited report**.

The loop you'll build:

```
question → o3-deep-research ──▶ search(query)   ┐
              ▲                  fetch(doc_id)    │  iterate until the model
              └───── tool results ◀──────────────┘  stops calling tools
                                   │
                                   ▼
                         gpt-4.1-mini synthesises a cited report
```

![The inference path](../../assets/inference-path.png)

!!! note "One project, two model roles"
    The reference deploys `o3-deep-research` in a separate region behind an APIM gateway. In
    our single-project setup both deployments live on the **same** project, so one
    `get_openai_client()` serves both. Deep-research models are **preview** and can run for
    minutes — pin `azure-ai-projects` / `openai` in `pyproject.toml` if a shape drifts."""),

    md("""\
## 1. Configure

Two model deployments: the **research** model that does the planning/tool-calling, and the
**synthesis** model that writes the report. `RESEARCH_MODEL` defaults to `o3-deep-research`."""),
    code("""\
import os, json, time
from dotenv import load_dotenv

load_dotenv()  # reads .env from the repo root

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
RESEARCH_MODEL   = os.environ.get("RESEARCH_MODEL", "o3-deep-research")
SYNTHESIS_MODEL  = os.environ.get("CHAT_MODEL", "gpt-4.1-mini")
MAX_ITERATIONS   = 6   # safety cap on the research loop

print("Project   :", PROJECT_ENDPOINT)
print("Research  :", RESEARCH_MODEL)
print("Synthesis :", SYNTHESIS_MODEL)"""),
    md("""\
!!! note "Expected output"
    ```
    Project   : https://<account>.services.ai.azure.com/api/projects/<project>
    Research  : o3-deep-research
    Synthesis : gpt-4.1-mini
    ```
    Splitting the roles is deliberate: reasoning models are powerful but slow and pricey, so
    you let one *think* and a cheaper one *write*."""),

    md("""\
## 2. Build the client

The familiar bootstrap. Because a deep-research call can run for **minutes**, we derive a
long-timeout view of the client with `.with_options(...)` for the research loop, and use the
default client for fast synthesis."""),
    code("""\
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

credential     = DefaultAzureCredential()
project_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
openai_client  = project_client.get_openai_client()

research_client = openai_client.with_options(timeout=600.0)  # o3 can run several minutes

print("openai_client   : ready")
print("research_client : ready (timeout=600s)")"""),
    md("""\
!!! note "Expected output"
    ```
    openai_client   : ready
    research_client : ready (timeout=600s)
    ```
    A read-timeout error during research almost always means the default 60s timeout — the
    `with_options(timeout=600.0)` view above is what prevents it."""),

    md("""\
## 3. A knowledge source + two tools

The model can't search the open web here — it researches a **knowledge source** you control.
We use a tiny in-notebook corpus of paper abstracts so the lab is self-contained, and expose
it through two function tools the model will call: **`search`** (find relevant docs) and
**`fetch`** (read one in full)."""),
    code("""\
# A miniature corpus — in production this is a Foundry IQ knowledge base (see note).
CORPUS = {
    "doc-001": {"title": "Prototypical Networks for Few-Shot Learning",
                "text": "Prototypical networks learn a metric space where classification is "
                        "performed by computing distances to per-class prototypes. Strong on "
                        "miniImageNet 5-way 5-shot; simpler than matching networks."},
    "doc-002": {"title": "Model-Agnostic Meta-Learning (MAML)",
                "text": "MAML learns an initialization that adapts to a new task in a few "
                        "gradient steps. Model-agnostic; competitive few-shot accuracy but "
                        "costly second-order gradients."},
    "doc-003": {"title": "Matching Networks for One Shot Learning",
                "text": "Matching networks use attention over a labelled support set to "
                        "classify with one example per class; introduced episodic training."},
    "doc-004": {"title": "Linformer: Self-Attention with Linear Complexity",
                "text": "Linformer projects keys and values to a low-rank form, reducing "
                        "self-attention from O(n^2) to O(n) in sequence length."},
}

def tool_search(query: str) -> dict:
    \"\"\"Return doc summaries whose title/text match any query keyword.\"\"\"
    terms = {w.lower().strip('.,?') for w in query.split() if len(w) > 3}
    hits = [{"id": i, "title": d["title"], "summary": d["text"][:120] + "..."}
            for i, d in CORPUS.items()
            if terms & set((d["title"] + " " + d["text"]).lower().split())]
    print(f"   search({query[:48]!r}) -> {len(hits)} hit(s)")
    return {"results": hits}

def tool_fetch(document_id: str) -> dict:
    \"\"\"Return the full document by id.\"\"\"
    print(f"   fetch({document_id!r})")
    doc = CORPUS.get(document_id)
    return doc | {"id": document_id} if doc else {"error": "not found"}

TOOLS = [
    {"type": "function", "function": {
        "name": "search", "description": "Search the research corpus; returns doc ids + summaries.",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "fetch", "description": "Fetch the full text of one document by its id.",
        "parameters": {"type": "object",
                       "properties": {"document_id": {"type": "string"}}, "required": ["document_id"]}}},
]
print(f"Corpus: {len(CORPUS)} docs | tools: search, fetch")"""),
    md("""\
!!! note "Expected output"
    ```
    Corpus: 4 docs | tools: search, fetch
    ```

!!! tip "Swap in a real knowledge base"
    In production the `search`/`fetch` bodies call a **Foundry IQ knowledge base** instead of
    a dict — the same grounding you built in """ +
    sibling_link("04-grounding-rag-foundry-iq", "M4") + """. Read its endpoint from `.env`
    (`SEARCH_ENDPOINT`) and POST to the KB's `retrieve` API; provisioning the KB is covered
    in the """ + page_link("setup", "Platform docs") + """. The loop below is unchanged."""),

    md("""\
## 4. The deep-research loop

This is the heart of the lab. We hand the **research model** the question + tool schemas,
then loop: each turn the model either **calls tools** (we execute them and feed results back)
or **stops** — signalling it has enough to conclude. We track iterations and tool calls so
the process is observable, and cap the loop for safety."""),
    code("""\
def run_deep_research(question: str) -> dict:
    \"\"\"Agentic loop: o3-deep-research plans + calls tools until it's ready to conclude.\"\"\"
    messages = [
        {"role": "system", "content":
            "You are a deep-research assistant. Investigate the user's question using the "
            "search and fetch tools: search broadly, fetch the most relevant documents, and "
            "search again to fill gaps. Cite document ids like [doc-001]. If the corpus does "
            "not cover the question, say so explicitly rather than guessing."},
        {"role": "user", "content": question},
    ]
    tool_calls_made, iterations = [], 0

    for iterations in range(1, MAX_ITERATIONS + 1):
        print(f"Iteration {iterations}")
        msg = research_client.chat.completions.create(
            model=RESEARCH_MODEL, messages=messages, tools=TOOLS,
        ).choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            break  # model is done researching

        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            result = tool_search(**args) if call.function.name == "search" else tool_fetch(**args)
            tool_calls_made.append(call.function.name)
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(result)})

    findings = msg.content or "(model concluded without a summary message)"
    return {"findings": findings, "iterations": iterations,
            "tool_calls": tool_calls_made, "messages": messages}

print("run_deep_research() ready")"""),
    md("""\
!!! note "Expected output"
    ```
    run_deep_research() ready
    ```
    The loop ends when the model returns a message with **no `tool_calls`** — that's o3
    signalling "I've gathered enough." The `MAX_ITERATIONS` cap is your guardrail against a
    model that keeps searching forever."""),

    md("""\
## 5. Run a question → synthesise a cited report

Pose a real question, run the loop, then hand the model's findings to the **synthesis model**
to format a clean report. Splitting *research* from *writing* keeps the expensive reasoning
focused and lets a fast model do the prose."""),
    code("""\
question = ("What are the main approaches to few-shot learning in the corpus, "
            "and how do they differ? Cite the documents.")

research = run_deep_research(question)

report = openai_client.chat.completions.create(
    model=SYNTHESIS_MODEL,
    messages=[
        {"role": "system", "content": "You are a research report writer. Turn the findings "
         "into a concise, well-structured report. Preserve every [doc-id] citation."},
        {"role": "user", "content": f"Question:\\n{question}\\n\\nFindings:\\n{research['findings']}"},
    ],
).choices[0].message.content

print(f"\\nIterations : {research['iterations']}")
print(f"Tool calls : {research['tool_calls']}\\n")
print(report)"""),
    md("""\
!!! note "Expected output"
    ```
    Iteration 1
       search('few-shot learning approaches') -> 3 hit(s)
    Iteration 2
       fetch('doc-001')
       fetch('doc-002')
       fetch('doc-003')
    Iteration 3

    Iterations : 3
    Tool calls : ['search', 'fetch', 'fetch', 'fetch']

    ## Few-Shot Learning Approaches in the Corpus

    The corpus describes three distinct families:

    - **Metric-based** — Prototypical Networks classify by distance to per-class
      prototypes [doc-001], while Matching Networks use attention over a support set
      and introduced episodic training [doc-003].
    - **Optimization-based** — MAML learns an initialization that adapts in a few
      gradient steps, at the cost of second-order gradients [doc-002].

    Metric methods are simpler and cheaper; MAML is model-agnostic but costlier...
    ```
    Notice the **shape**: search → fetch the promising hits → conclude → cited report. The
    model planned the investigation; you only supplied the tools."""),

    md("""\
## 6. Respect the knowledge boundary

A trustworthy researcher admits what it *doesn't* know. Ask something the corpus can't
cover and watch the model **decline** rather than hallucinate — the system prompt told it to
say so explicitly when the corpus falls short."""),
    code("""\
oos = run_deep_research("What are the latest breakthroughs in nuclear fusion energy?")

print(f"\\nIterations : {oos['iterations']}")
print(f"Tool calls : {oos['tool_calls']}\\n")
print(oos["findings"])"""),
    md("""\
!!! note "Expected output"
    ```
    Iteration 1
       search('nuclear fusion energy breakthroughs') -> 0 hit(s)
    Iteration 2

    Iterations : 2
    Tool calls : ['search']

    The corpus does not contain any documents on nuclear fusion energy — it covers
    few-shot learning and transformer efficiency in NLP. I can't answer this from the
    available knowledge source.
    ```

!!! tip "Grounding beats guessing"
    The empty `search` result is the signal: with nothing to fetch, a well-prompted research
    model reports the **boundary** instead of inventing citations. This honesty is exactly
    what you'll measure in """ + sibling_link("09-evaluation", "M9 · Evaluation") + """."""),

    md("""\
## 🧪 Your turn

1. **Add a document.** Drop a new `doc-005` about *cross-lingual transfer* into `CORPUS`, then
   ask a multilingual-NLP question — confirm the loop searches, fetches it, and cites it.
2. **Watch it iterate.** Ask a comparison that spans two topics (*"Contrast few-shot metric
   methods with efficient attention"*) and print `research['tool_calls']` — you should see
   **multiple** search/fetch rounds.
3. **Tune the cap.** Lower `MAX_ITERATIONS` to `1` and observe the loop stop early with a
   thinner report; raise it and watch the model dig deeper. This is the cost/quality dial.

---

✅ **You ran an agentic deep-research loop — plan, search, fetch, iterate — and turned its
findings into a cited report, with the model honouring its knowledge boundary.** Next: measure
answer quality, groundedness, and safety systematically.
""" + next_link("09-evaluation", "M9 · Evaluation")),
]

write_notebook(
    "docs/modules/08-deep-research.ipynb",
    cells,
    kernel_name=KERNEL,
    kernel_display=KERNEL_DISPLAY,
)
