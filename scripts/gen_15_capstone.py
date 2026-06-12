"""Generate Module 15 — Capstone.

Synthesizes the whole workshop: build ONE agent that is grounded (M4),
tool-using (M3), evaluated (M9), and observable (M10) — then point to the
enterprise topics the workshop deliberately deferred.
"""
from nbbuild import md, code, write_notebook, sibling_link, page_link

KERNEL = "foundry-workshop"
KERNEL_DISPLAY = "Microsoft Foundry: End-to-End Workshop"

cells = [
    md("""\
# M15 · Capstone

> **Goal:** combine everything — a grounded, tool-using, evaluated, observable agent — into one coherent build, then see where to go next.
> **You'll use:** `PromptAgentDefinition` with tools + knowledge, the Responses API, an evaluator, and tracing.

---

This is the victory lap. You've built each capability in isolation; now you'll wire
the important ones into a **single agent** and run it end to end. Then we'll map the
enterprise topics this workshop deliberately kept out of your way.

![Microsoft Foundry — one unified platform](../../assets/platform-overview.png)

!!! tip "What we're assembling"
    A **"Contoso Support"** agent that:

    - is **grounded** on a small knowledge base (""" + sibling_link("04-grounding-rag-foundry-iq", "M4") + """),
    - can call a **custom tool** (""" + sibling_link("03-tools-and-function-calling", "M3") + """),
    - is **evaluated** for quality before we trust it (""" + sibling_link("09-evaluation", "M9") + """),
    - and is **traced** so we can watch it in production (""" + sibling_link("10-observability-tracing", "M10") + """)."""),

    md("""\
## 1. Bootstrap (the pattern you now know by heart)

Same four lines from """ + sibling_link("01-first-inference", "M1") + """ — one client,
reused for everything."""),
    code("""\
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()
PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
CHAT_MODEL       = os.environ.get("CHAT_MODEL", "gpt-4.1-mini")

credential     = DefaultAzureCredential()
project_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
openai_client  = project_client.get_openai_client()

print("Ready to build the capstone agent on:", CHAT_MODEL)"""),
    md("""\
!!! note "Expected output"
    ```
    Ready to build the capstone agent on: gpt-4.1-mini
    ```"""),

    md("""\
## 2. A tool the agent can call

We give the support agent one **custom function tool** — looking up an order's status —
exactly as you did in """ + sibling_link("03-tools-and-function-calling", "M3") + """.
In a real build this would hit your order system; here it's a stub."""),
    code("""\
import json

# The local implementation the agent's tool call maps to.
def get_order_status(order_id: str) -> dict:
    orders = {
        "A-1001": {"status": "shipped",   "eta": "2026-06-15"},
        "A-1002": {"status": "processing", "eta": "2026-06-20"},
    }
    return orders.get(order_id, {"status": "not_found"})

# The tool schema advertised to the model (function calling).
order_tool = {
    "type": "function",
    "name": "get_order_status",
    "description": "Look up the status and ETA of a customer order by its ID.",
    "parameters": {
        "type": "object",
        "properties": {"order_id": {"type": "string", "description": "e.g. A-1001"}},
        "required": ["order_id"],
    },
}
print("Tool defined:", order_tool["name"])"""),
    md("""\
!!! note "Expected output"
    ```
    Tool defined: get_order_status
    ```"""),

    md("""\
## 3. Define the capstone agent

We create a **versioned agent** (""" + sibling_link("02-your-first-agent", "M2") + """)
whose definition carries both **instructions** and the **tool**. In a full build you'd
also attach a Foundry IQ **knowledge base** (""" + sibling_link("04-grounding-rag-foundry-iq", "M4") + """)
here so answers are grounded with citations."""),
    code("""\
from azure.ai.projects.models import PromptAgentDefinition

AGENT_NAME = "contoso-support-agent"

agent = project_client.agents.create_version(
    agent_name=AGENT_NAME,
    definition=PromptAgentDefinition(
        model=CHAT_MODEL,
        instructions=(
            "You are Contoso's support agent. Be concise and friendly. "
            "Use the get_order_status tool whenever a customer asks about an order. "
            "If grounding knowledge is attached, cite it. Never invent order data."
        ),
        tools=[order_tool],
        # knowledge=[...]   # attach a Foundry IQ knowledge base in a full build (M4)
    ),
)
print("Name    :", agent.name)
print("Version :", agent.version)"""),
    md("""\
!!! note "Expected output"
    ```
    Name    : contoso-support-agent
    Version : 1
    ```

!!! warning "Tool + knowledge APIs are evolving"
    The exact `tools` / `knowledge` field shapes on `PromptAgentDefinition` are
    pre-release. If an import or field name fails, re-check """ +
    sibling_link("03-tools-and-function-calling", "M3") + """ and """ +
    sibling_link("04-grounding-rag-foundry-iq", "M4") + """, and pin versions in
    `pyproject.toml`."""),

    md("""\
## 4. Run it — with the tool-call loop

Invoke through the Responses API. If the model decides to call our tool, we run the
function locally and feed the result back so it can finish its answer — the
`function_call → function_call_output` loop from """ +
sibling_link("13-human-in-the-loop-and-rest", "M13") + """."""),
    code("""\
def run_support(user_msg: str) -> str:
    resp = openai_client.responses.create(
        input=[{"role": "user", "content": user_msg}],
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )

    # Did the model ask to call our tool?
    tool_calls = [o for o in resp.output if getattr(o, "type", None) == "function_call"]
    if not tool_calls:
        return resp.output_text

    # Execute each requested tool and return the outputs.
    outputs = []
    for call in tool_calls:
        args = json.loads(call.arguments)
        result = get_order_status(**args)
        outputs.append({
            "type": "function_call_output",
            "call_id": call.call_id,
            "output": json.dumps(result),
        })

    final = openai_client.responses.create(
        input=outputs,
        previous_response_id=resp.id,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    return final.output_text

print(run_support("Where is my order A-1001?"))"""),
    md("""\
!!! note "Expected output"
    ```
    Your order A-1001 has shipped and is expected to arrive on 2026-06-15.
    Is there anything else I can help you with?
    ```
    The model called `get_order_status("A-1001")`, we returned the stub data, and it
    composed the final reply from that tool result."""),

    md("""\
## 5. Evaluate before you trust it

A capstone agent isn't done until it's **measured** (""" +
sibling_link("09-evaluation", "M9") + """). Score a couple of responses for
**relevance** against a tiny inline test set."""),
    code("""\
from azure.ai.evaluation import RelevanceEvaluator, AzureOpenAIModelConfiguration

judge = AzureOpenAIModelConfiguration(
    azure_endpoint=PROJECT_ENDPOINT,
    azure_deployment=CHAT_MODEL,
)
relevance = RelevanceEvaluator(model_config=judge)

cases = [
    {"query": "Where is my order A-1001?", "response": run_support("Where is my order A-1001?")},
    {"query": "What's the ETA on A-1002?",  "response": run_support("What's the ETA on A-1002?")},
]
for c in cases:
    score = relevance(query=c["query"], response=c["response"])
    print(f"{c['query'][:28]:30} relevance = {score['relevance']}/5")"""),
    md("""\
!!! note "Expected output"
    ```
    Where is my order A-1001?      relevance = 5/5
    What's the ETA on A-1002?      relevance = 4/5
    ```
    Scores will vary. The point: you have a **number** to gate releases on, not a vibe."""),

    md("""\
## 6. Make it observable

Finally, turn on tracing (""" + sibling_link("10-observability-tracing", "M10") + """)
so every capstone run emits spans to **Application Insights**. One call wires it up;
after that your `run_support(...)` calls are traced automatically."""),
    code("""\
from azure.monitor.opentelemetry import configure_azure_monitor

conn = os.environ.get("APP_INSIGHTS_CONN_STRING")
if conn:
    configure_azure_monitor(connection_string=conn)
    # project_client.telemetry / AIProjectInstrumentor wiring as in M10
    print("Tracing on — capstone runs now export spans to App Insights.")
else:
    print("Set APP_INSIGHTS_CONN_STRING in .env to enable tracing (see M10).")"""),
    md("""\
!!! note "Expected output"
    ```
    Tracing on — capstone runs now export spans to App Insights.
    ```
    In the portal's **Monitor** tab (or via KQL) you'll see a span per `responses.create`
    call, including the tool call — the full picture of what your agent did."""),

    md("""\
## 🧪 Your turn — make it yours

1. **Ground it for real.** Attach a Foundry IQ knowledge base from """ +
sibling_link("04-grounding-rag-foundry-iq", "M4") + """ and add a question whose
answer must come from a document — confirm the agent cites it.
2. **Add a guardrail.** Pin a guardrail policy from """ +
sibling_link("11-guardrails", "M11") + """ to the deployment and try a prompt-injection
input; confirm it's blocked.
3. **Harden + measure.** Run the """ + sibling_link("12-red-teaming", "M12") + """ scan
against your capstone agent, then add the worst-scoring prompts to your """ +
sibling_link("09-evaluation", "M9") + """ test set and re-evaluate."""),

    md("""\
## 🚀 Where to go next

You built the *application* layer end to end. The reference series this workshop draws
from goes deeper on the **enterprise platform** — pick your next thread:

| Topic | What it adds | Start with |
|:--|:--|:--|
| **Hosted agents** | Deploy your agent as a containerized (ACR-backed) service for portability and scale. | Reference lab `08-03-hosted-agents` |
| **Multi-agent at scale** | Grow """ + sibling_link("07-multi-agent-orchestration", "M7") + """ into a production router + specialist fleet. | Reference area `11` |
| **Content Understanding** | Plumb Azure AI Content Understanding (documents, audio, video) behind your project. | Reference area `09` |
| **Hub-and-spoke infra** | The Bicep/APIM topology, per-team quotas, and a governed gateway from """ + page_link("concepts", "Concepts") + """. | Reference area `05` |
| **Governance with policy** | Deny ungoverned deployments and force all traffic through the gateway. | Reference area `06` |
| **Publishing** | Surface your agent in Microsoft 365, Teams, and BizChat. | Control plane docs |

Read the """ + page_link("concepts", "Concepts") + """ page once more — now every box in
that diagram is something you've actually built.

---

✅ **You shipped a grounded, tool-using, evaluated, observable agent on Microsoft
Foundry — end to end.** That's the whole workshop. Nicely done.

← Back to """ + page_link("index", "the workshop home") + """ · revisit any lab from there."""),
]

write_notebook(
    "docs/modules/15-capstone.ipynb",
    cells,
    kernel_name=KERNEL,
    kernel_display=KERNEL_DISPLAY,
)
