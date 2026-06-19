# MCP tool servers

> How to **provision the MCP server** that [M5 · MCP Tools](../modules/05-mcp-tools.ipynb)
> connects to — deploy it, read its URL + key, and (optionally) register it in the
> Foundry **tool catalog** so agents reference it by connection id.

[M5 · MCP Tools](../modules/05-mcp-tools.ipynb) connects an agent to a remote **Model
Context Protocol (MCP)** server. The lab itself **assumes that server already exists** —
it only reads `MCP_SERVER_URL` / `MCP_SERVER_LABEL` from `.env` and wires them to an
agent. This page covers the missing half: **how to stand the server up**.

You have two practical options:

| Option | Effort | When to use |
|:--|:--|:--|
| **A · Deploy the reference Azure Functions MCP server** | ~10 min, needs Azure | You want the exact 37-tool "project tracker" used by the reference lab. |
| **B · Run any MCP server you already have** | minimal | You have another MCP endpoint (hosted or local) and just want M5 to call it. |

!!! tip "Just reading along? You can skip this."
    M5 prints its **Expected output** in prose, so you can read the whole lab without a
    server. Provision one only when you want to *run* the cells.

---

## Option A — Deploy the reference Azure Functions MCP server

The reference series (`08-agents/08-05-contoso-pmo-mcp`) ships a multi-tool MCP server
built on the **Azure Functions MCP extension**. Azure Functions exposes MCP tools over a
built-in **SSE endpoint** at `/runtime/webhooks/mcp/sse`, protected by a system key — which
is exactly the URL shape M5 expects (`https://<host>/runtime/webhooks/mcp/sse?code=<key>`).

### 1. Prerequisites

- The toolchain from [Setup](../setup.md) (`az login`, an Azure subscription).
- **Azure Functions Core Tools v4** — [install](https://learn.microsoft.com/azure/azure-functions/functions-run-local).
- The reference server source. Clone the upstream reference repo and change into the
  Contoso PMO MCP sample:

  ```bash
  git clone https://github.com/microsoft/foundry-samples.git
  cd foundry-samples/08-agents/08-05-contoso-pmo-mcp
  ```

  (Folder names in the upstream repo move occasionally — if the path differs, search the
  repo for the `08-05-contoso-pmo-mcp` sample.)

### 2. Create the Function App and deploy

Create a Flex Consumption Function App (and its storage account), then publish the code:

```bash
RG=foundry-workshop-rg
LOCATION=eastus
STORAGE=fwmcp$RANDOM
APP=foundry-workshop-mcp-$RANDOM

az group create -n $RG -l $LOCATION
az storage account create -n $STORAGE -g $RG -l $LOCATION --sku Standard_LRS
az functionapp create -n $APP -g $RG \
  --storage-account $STORAGE \
  --flexconsumption-location $LOCATION \
  --runtime python --runtime-version 3.12 --functions-version 4

# from the sample directory:
func azure functionapp publish $APP
```

!!! tip "Prefer `azd`?"
    If the sample includes an `azure.yaml`, `azd up` provisions **and** deploys in one
    step. Either path leaves you with a running Function App.

### 3. Read the server URL + key

The MCP SSE endpoint is guarded by the **`mcp_extension`** system key. Fetch it and
assemble the full URL:

```bash
HOST=$(az functionapp show -n $APP -g $RG --query defaultHostName -o tsv)
KEY=$(az functionapp keys list -n $APP -g $RG \
  --query "systemKeys.mcp_extension" -o tsv)

echo "MCP_SERVER_URL=https://$HOST/runtime/webhooks/mcp/sse?code=$KEY"
```

!!! danger "Treat the key like a password"
    The `?code=<key>` query string **is** the credential for the server. Keep it in
    `.env` (git-ignored) — never paste it into a notebook cell or commit it.

### 4. Set the M5 variables

Add these to your `.env` (see [Setup → Configure](../setup.md)):

```ini
MCP_SERVER_URL=https://<host>/runtime/webhooks/mcp/sse?code=<mcp_extension-key>
MCP_SERVER_LABEL=project_tracker
```

`MCP_SERVER_LABEL` is just a short name that **namespaces** the server's tools inside an
agent, so multiple MCP servers can coexist. M5 §1–§5 needs only these two values.

---

## Option B — Use any MCP server you already have

M5 is server-agnostic: any reachable MCP endpoint works. Point the same two variables at
it —

```ini
MCP_SERVER_URL=https://<your-host>/<your-mcp-endpoint>     # include any ?code= / token
MCP_SERVER_LABEL=project_tracker
```

— and re-run the lab. The exact tool **names** in the output will differ (M5 happens to
call `list_overdue_tasks`), but the SDK flow — attach tool → ask → watch `mcp_call`
items — is identical. The closely related [M5b · Work IQ](../modules/05b-work-iq.ipynb)
lab follows this same pattern against the Microsoft 365 Work IQ MCP server.

---

## Register it in the tool catalog (optional — M5 §6)

M5's final section references the server through the **Foundry tool catalog** instead of
baking the key into each agent. Register the server **once** as a project connection,
then agents reference it by **connection id** — rotate the key in the connection and every
agent picks up the change.

1. In the **Microsoft Foundry** portal, open your project → **Management center →
   Connected resources** (the same **[connections](02-architecture-and-projects.md#3-connections)**
   surface used for Azure AI Search and Application Insights).
2. Add a **Custom / MCP** connection: paste the `MCP_SERVER_URL` (with its key) as the
   target and give it a name, e.g. `project-tracker-mcp`. The credential now lives in the
   connection, not in agent code.
3. Record the connection name in `.env`:

   ```ini
   MCP_CONNECTION=project-tracker-mcp
   ```

M5 §6 then resolves it with `project_client.connections.get(MCP_CONNECTION)` and passes
`project_connection_id` instead of an inline key.

!!! warning "Approvals for write-capable servers"
    M5 uses `require_approval="never"` because the project tracker is read-mostly. If
    your server has tools that **write** or spend money, register it the same way but set
    `require_approval="always"` in the agent so each call surfaces for a human to approve.

---

→ Back to **[M5 · MCP Tools](../modules/05-mcp-tools.ipynb)**, or review
**[Control plane & governance](03-control-plane-and-governance.md)** for the enterprise
deployment story.
