"""Generate Module 1 — First Inference.

Canonical exemplar for the workshop. Mirrors the upstream reference
07-model-inference/07-01, simplified to a single Foundry project +
DefaultAzureCredential (no APIM gateway, no team spokes).
"""
from nbbuild import md, code, write_notebook, next_link, sibling_link, page_link

KERNEL = "foundry-workshop"
KERNEL_DISPLAY = "Microsoft Foundry: End-to-End Workshop"

cells = [
    md("""\
# M1 · First Inference

> **Goal:** make your first model calls on Foundry — chat, embeddings, streaming, and the Responses API — all from one client.
> **You'll use:** `AIProjectClient`, `get_openai_client()`, `chat.completions`, `embeddings`, `responses`.

---

Every lab in this workshop starts the same way: authenticate with
`DefaultAzureCredential`, build an **`AIProjectClient`** from your project endpoint,
and ask it for an OpenAI-compatible client. That one client gives you **chat**,
**embeddings**, and the **Responses API** that later powers agents and tools.

![The inference path](../../assets/inference-path.png)

If you haven't set up your project and `.env` yet, do the
""" + page_link("setup", "Setup") + """ first."""),

    md("""\
## 1. Configure

Every lab reads the same variables from your `.env` (see
""" + page_link("setup", "Setup") + """). We load them and grab the two model
deployment names we'll use here."""),
    code("""\
import os
from dotenv import load_dotenv

load_dotenv()  # reads .env from the repo root

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
CHAT_MODEL       = os.environ.get("CHAT_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL  = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")

print("Project :", PROJECT_ENDPOINT)
print("Chat    :", CHAT_MODEL)
print("Embed   :", EMBEDDING_MODEL)"""),
    md("""\
!!! note "Expected output"
    ```
    Project : https://<account>.services.ai.azure.com/api/projects/<project>
    Chat    : gpt-4.1-mini
    Embed   : text-embedding-3-large
    ```
    The values come straight from your `.env` — no secrets in the notebook."""),

    md("""\
## 2. Build the client

`DefaultAzureCredential` uses your `az login` identity (or a managed identity in
production). `AIProjectClient` is constructed from the project endpoint + that
credential; `get_openai_client()` returns the OpenAI-compatible client wired to your
project."""),
    code("""\
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

credential     = DefaultAzureCredential()
project_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
openai_client  = project_client.get_openai_client()

print("project_client : ready")
print("openai_client  : ready")"""),
    md("""\
!!! note "Expected output"
    ```
    project_client : ready
    openai_client  : ready
    ```
    A `DefaultAzureCredential` error here almost always means you need to run
    `az login`; a `403` means your identity lacks the **Azure AI Developer** role on
    the project."""),

    md("""\
## 3. Chat completions

The classic chat surface. You pass the **deployment name** (not a raw model id) and a
list of messages."""),
    code("""\
response = openai_client.chat.completions.create(
    model=CHAT_MODEL,
    messages=[
        {"role": "system", "content": "You are a concise technical assistant."},
        {"role": "user",   "content": "What is catastrophic forgetting in neural networks?"},
    ],
)

print("Model  :", response.model)
print("Tokens :", response.usage.total_tokens)
print()
print(response.choices[0].message.content)"""),
    md("""\
!!! note "Expected output"
    ```
    Model  : gpt-4.1-mini
    Tokens : 142
    Catastrophic forgetting is the tendency of a neural network to abruptly lose
    knowledge of previously learned tasks when it is trained on a new task...
    ```
    Token counts and wording will vary; the shape is what matters."""),

    md("""\
## 4. Embeddings

Turn text into vectors — the foundation for retrieval. You'll lean on this in
""" + sibling_link("04-grounding-rag-foundry-iq", "M4 · Grounding/RAG") + """. One call
embeds a batch of strings."""),
    code("""\
texts = [
    "Microsoft Foundry centralises model governance behind one platform.",
    "Embeddings turn text into vectors for semantic search.",
    "Each project authenticates with DefaultAzureCredential.",
]

result = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=texts)

print("Model      :", EMBEDDING_MODEL)
print("Dimensions :", len(result.data[0].embedding))
for i, item in enumerate(result.data):
    v = item.embedding
    print(f"[{i}] [{v[0]:.4f}, {v[1]:.4f}, {v[2]:.4f}, ...]  ({len(v)} dims)")"""),
    md("""\
!!! note "Expected output"
    ```
    Model      : text-embedding-3-large
    Dimensions : 3072
    [0] [-0.0123, 0.0456, -0.0789, ...]  (3072 dims)
    [1] [0.0234, -0.0567, 0.0891, ...]  (3072 dims)
    [2] [-0.0345, 0.0678, -0.0912, ...]  (3072 dims)
    ```"""),

    md("""\
## 5. Streaming

For responsive UIs, stream tokens as they're generated instead of waiting for the full
response."""),
    code("""\
stream = openai_client.chat.completions.create(
    model=CHAT_MODEL,
    messages=[{"role": "user", "content": "In one sentence, what is Microsoft Foundry?"}],
    stream=True,
)

for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()"""),
    md("""\
!!! note "Expected output"
    The sentence prints **incrementally**, a few tokens at a time:
    ```
    Microsoft Foundry is Azure's unified platform-as-a-service for building, governing,
    and operating enterprise AI models, agents, and apps.
    ```"""),

    md("""\
## 6. The Responses API

The **Responses API** is the modern, stateful surface that powers **agents** and
**tools** in every later lab. The minimal call takes a model and an `input`; the reply
is in `output_text`."""),
    code("""\
response = openai_client.responses.create(
    model=CHAT_MODEL,
    input="Name a planet with rings, in one short sentence.",
)

print(response.output_text)"""),
    md("""\
!!! note "Expected output"
    ```
    Saturn is a planet famous for its prominent ring system.
    ```

!!! tip "Why this matters"
    Hold onto this call. In the next lab you'll wrap a model in an **agent definition**
    and invoke it through this exact `responses.create(...)` surface — just with an
    `agent_reference` attached."""),

    md("""\
## 🧪 Your turn

1. **Swap the model.** If you deployed a reasoning model, set `REASONING_MODEL` in your
   `.env`, read it in cell 1, and re-run the Responses API call with it. Note how the
   answer style changes.
2. **Compare token usage.** Ask the chat model a long question vs. a short one and print
   `response.usage.total_tokens` for each.
3. **Embed and compare.** Embed two *similar* sentences and two *different* ones, then
   compute cosine similarity (`numpy.dot` on normalized vectors) — similar sentences
   should score higher.

---

✅ **You made chat, embedding, streaming, and Responses API calls from one client.**
Next: wrap a model in a versioned **agent** and invoke it.
""" + next_link("02-your-first-agent", "M2 · Your First Agent")),
]

write_notebook(
    "docs/modules/01-first-inference.ipynb",
    cells,
    kernel_name=KERNEL,
    kernel_display=KERNEL_DISPLAY,
)
