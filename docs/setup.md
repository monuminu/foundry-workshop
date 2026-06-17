# Setup — do this before the workshop

This takes about **15–20 minutes**. You'll install the toolchain, create a Foundry
project with a couple of model deployments, and run a smoke test that proves your
environment can reach Foundry.

!!! info "Two kinds of dependency"
    - To **read or build this site**, you only need the docs toolchain (`".[docs]"`).
    - To **run the labs** against Azure, you also need the runtime SDKs (`pip install -e .`),
      an `az login`, and a Foundry project. Both are covered below.

---

## 1. Azure prerequisites

You need an Azure subscription and these tools:

- **Azure CLI** v2.60+ — [install](https://learn.microsoft.com/cli/azure/install-azure-cli)
- **`cognitiveservices` CLI extension** — `az extension add -n cognitiveservices`
- **`uv`** (recommended) — [install](https://docs.astral.sh/uv/getting-started/installation/) — or plain `python -m venv`
- Signed in: **`az login`**

### Create a Foundry project + deploy models

In the **Microsoft Foundry (new)** portal:

1. **Create a project** (this also creates its Foundry account). Note its **project
   endpoint** — it looks like
   `https://<account>.services.ai.azure.com/api/projects/<project>`.
2. In **Build → Models**, deploy:
   - a chat model — **`gpt-4.1-mini`** (used everywhere),
   - an embeddings model — **`text-embedding-3-large`** (M4, M7),
   - *(optional)* a reasoning model — **`o4-mini`** (M1 notes, M13),
   - *(optional)* **`o3-deep-research`** (M8).
3. Give your signed-in identity the **Azure AI Developer** role on the project so
   `DefaultAzureCredential` can call it.

!!! tip "Don't have a project yet? You can still follow along"
    Every lab shows its **Expected output** in prose, so you can read the whole
    workshop without Azure. Provision the project when you're ready to run cells.

---

## 2. Get the code & install

```bash
git clone https://github.com/monuminu/foundry-workshop.git
cd foundry-workshop
```

=== "uv (recommended)"

    ```bash
    uv venv --python 3.12 .venv
    source .venv/bin/activate          # Windows: .venv\Scripts\activate
    uv pip install -e ".[docs]"        # site + notebook toolchain
    uv pip install -e .                # runtime SDKs to RUN the labs
    ```

=== "pip"

    ```bash
    python -m venv .venv
    source .venv/bin/activate          # Windows: .venv\Scripts\activate
    pip install -e ".[docs]"           # site + notebook toolchain
    pip install -e .                   # runtime SDKs to RUN the labs
    ```

!!! warning "Pre-release SDKs"
    Foundry's SDKs move fast. This workshop pins
    `azure-ai-projects>=2.1.0`, `azure-identity>=1.26.0b2`, and
    `agent-framework-*==1.0.0rc6` (see `pyproject.toml`). If an import breaks after an
    upstream release, pin back to these versions.

---

## 3. Register the Jupyter kernel

```bash
python -m ipykernel install --user --name foundry-workshop \
  --display-name "Microsoft Foundry: End-to-End Workshop"
```

When you open a lab notebook, select the **Microsoft Foundry: End-to-End Workshop**
kernel.

---

## 4. Configure your environment

Copy the template and fill in your values. **Every lab loads these exact variable
names** via `python-dotenv`, so set them once here:

```bash
cp .env.example .env     # then edit .env
```

```ini title=".env"
# Required for all labs
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
PROJECT_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project>
CHAT_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-large

# Optional — only needed by specific labs
REASONING_MODEL=o4-mini                                   # M1 notes, M13
RESEARCH_MODEL=o3-deep-research                           # M8
SEARCH_ENDPOINT=https://<search>.search.windows.net       # M4, M7
WORKIQ_MCP_URL=https://<host>/workiq/mcp                   # M5b (+ key)
WORKIQ_MCP_LABEL=work_iq                                   # M5b
APP_INSIGHTS_CONN_STRING=<application-insights-conn-str>  # M10
```

Authentication is **`DefaultAzureCredential`** throughout — your `az login` identity.
**No model keys live in notebooks.**

!!! danger "Never commit `.env`"
    `.env` is git-ignored. Keep your subscription id, endpoints, and any keys out of
    version control.

!!! info "Optional: M5b · Work IQ prerequisites"
    The **[Work IQ](modules/05b-work-iq.ipynb)** lab grounds an agent in live Microsoft 365
    work context. To *run* it (reading the lab needs nothing extra) you also need:

    - A licensed **Microsoft 365 tenant**
    - **Node.js 22+**
    - **Tenant admin consent** for the Work IQ application — this `client_id` is the
      fixed, Microsoft-provided Work IQ application ID (the same for every tenant; do not
      substitute your own). Grant consent at
      `https://login.microsoftonline.com/{your-tenant-id}/adminconsent?client_id=ba081686-5d24-4bc6-a0d6-d034ecffed87`
    - The **Work IQ CLI** (`npm install -g @microsoft/workiq`, or run on demand with
      `npx -y @microsoft/workiq mcp`)
    - Accept the EULA once: `workiq accept-eula`

    See the upstream [Work IQ](https://github.com/microsoft/iq-series/tree/main/Work-IQ)
    project for the full admin guide.

---

## 5. Smoke test

Confirm your environment can construct the client and reach your project. Save this as
`smoke_test.py` and run `python smoke_test.py`:

```python
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()

project_client = AIProjectClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)
openai_client = project_client.get_openai_client()

resp = openai_client.responses.create(
    model=os.environ.get("CHAT_MODEL", "gpt-4.1-mini"),
    input="Reply with exactly: Foundry is ready.",
)
print(resp.output_text)
```

**Expected output:**

```
Foundry is ready.
```

If you see that line, you're set. (A `401`/`403` means your identity lacks the **Azure
AI Developer** role; a `DefaultAzureCredential` error usually means you need
`az login`.)

---

You're ready. → Read the **[Concepts](concepts.md)**, then start
**[M1 · First inference](modules/01-first-inference.ipynb)**.
