# IMO Health Diagnosis Specificity Agent

Complete Build Guide - Databricks AI Agent

End-to-end guide to build, configure, and deploy the IMO Diagnosis Specificity Agent using Databricks Supervisor Agent with MCP tools.

---

## 1. About IMO Health

IMO (Intelligent Medical Objects) Health provides clinical terminology and mapping solutions for healthcare. IMO APIs help normalize medical terms and traverse knowledge graphs to find the most specific diagnosis codes (ICD-10).

---

## 2. About Databricks AI Agents

Databricks AI Agent Framework allows you to build, test, and deploy AI agents with access to external tools and data. It supports:

- Multiple LLM models (Claude, Llama, GPT, etc.)
- MCP (Model Context Protocol) tool integration via Unity Catalog
- Supervisor Agent for multi-tool orchestration
- Built-in serving endpoints for production deployment
- AI Playground for testing and validation

---

## 3. Prerequisites

Before you start, make sure you have:

| Requirement | Details |
|---|---|
| Databricks workspace | With Unity Catalog enabled |
| Workspace access | Login credentials for your Databricks instance |
| IMO Health MCP Gateway URL | Provided by IMO team (e.g., `https://api.imohealth.com/mcp`) |
| IMO Auth Details | Client ID, Client Secret, Auth URLs (provided by IMO team) |
| Unity AI Gateway | Beta enabled on your workspace |
| Browser | Edge or Chrome (latest) |

---

## 4. Purpose of This Guide

This guide walks you through building a Clinical Diagnostic Specificity Agent in Databricks that finds the most specific diagnosis for a patient visit using the IMO Knowledge Graph. The agent connects to IMO APIs via an MCP (Model Context Protocol) server registered as a Unity Catalog connection. This serves as a guide for anyone who wants to build an Agent using the capabilities of the IMO MCP server on the Databricks platform.

---

## 5. Login to Databricks Workspace

### Step 1: Search for Databricks Account Console

1. Open your browser (Edge or Chrome)
2. Search for **"databricks account console"** in Bing/Google
3. Click on **"Databricks - Sign In"** link (`https://accounts.cloud.databricks.com`)

<img src="databricks-images/00_bing_search.png" width="700" alt="Search Databricks Account Console">

### Step 2: Log In with Email

1. The Databricks **Log in** page will appear
2. Enter your **Email** (the email registered during account creation)
3. Click **Continue**

<img src="databricks-images/00_databricks_login.png" width="700" alt="Databricks Login Page">

### Step 3: Enter Verification Code

1. Databricks will send a **verification code** to your registered email
2. Check your email inbox for the 6-digit code
3. Enter the verification code in the input boxes
4. You will be logged in after successful verification

<img src="databricks-images/00_databricks_verify.png" width="700" alt="Databricks Verification Code">

> **Note:** The verification code is sent to the email registered during Databricks account creation.

### Step 4: Verify You Are in the Correct Workspace

1. After login, you will land on the **"Welcome to Databricks"** Home page
2. Check the top-right corner shows **Production** (or your workspace name)
3. You should see the left sidebar with: Workspace, Recents, Catalog, Jobs & Pipelines, Compute, Discover, Marketplace, etc.

<img src="databricks-images/00_databricks_home.png" width="700" alt="Databricks Home Page">

---

## 6. Find the IMO MCP Connection in Unity Catalog

> **Note:** The MCP connection (`imo-health-mcp-gateway`) is already created in Databricks.

### Step 1: Navigate to Catalog

1. Click **Catalog** in the left sidebar
2. Click the **Connect** button (top-right of Catalog page)

<img src="databricks-images/01_catalog_page.png" width="700" alt="Catalog Page with Connect Button">

### Step 2: Open Connections

1. From the **Connect** dropdown, click **Connections** (Access external systems)

<img src="databricks-images/01_catalog_connect_dropdown.png" width="700" alt="Connect Dropdown - Connections">

### Step 3: Find the MCP Connection

1. You will see the **External Data** page with the **Connections** tab
2. Find **imo-health-mcp-gateway** in the connections list
3. Click on it to open the connection details

<img src="databricks-images/01_catalog_connections.png" width="700" alt="External Data - Connections List">

### Step 4: Verify Connection Details

You will see the connection detail page showing:

| Field | Value |
|---|---|
| Connection name | `imo-health-mcp-gateway` |
| Description | mcp gateway in imo health for mcp usage |
| Connection type | HTTP |
| URL | `https://api.imohealth.com:443/mcp` |
| Owner | svc_terraform |

<img src="databricks-images/02_connection_details.png" width="700" alt="MCP Connection Details">

### Step 5: Login and Authenticate

1. Click the **Login** button (top-right, blue button)
2. The IMO Health login page will appear
3. Enter your **Email** and **Password**
4. Click **LOGIN**
5. This completes the OAuth authentication with IMO Health

<img src="databricks-images/03_imo_health_login.png" width="700" alt="IMO Health Login">

> **Note:** Each user must perform this login once to authenticate their session with the IMO MCP Gateway.

---

## 7. Install MCP from Databricks Marketplace (Recommended)

The IMO Health MCP server is available on the Databricks Marketplace. This is the easiest way to add it as a tool for the AI Playground and Supervisor Agent.

### Step 6: Open Databricks Marketplace

1. Click **Marketplace** in the left sidebar
2. You will see the **Databricks Marketplace** page with "Production apps. Deployed to your data."
3. In the **"Search for products"** bar, type **"IMO"** or **"IMO Health"**

<img src="databricks-images/04_marketplace_home.png" width="700" alt="Databricks Marketplace Home">

### Step 7: Install the MCP Server

1. Click on the **IMO Health MCP Server** listing from search results
2. You will see the MCP server detail page with Overview, Tools, and Details
3. Click **Install** button (top-right)
4. Select the target catalog and schema where you want to install (e.g., `genai_workshop.poc`)
5. Click **Install** to confirm

<img src="databricks-images/04_marketplace_install.png" width="700" alt="Marketplace MCP Server Install">

### Step 8: Authenticate After Installation

1. After installation, navigate to the installed MCP service in your catalog
2. Click **Login** to authenticate with IMO Health
3. Complete the OAuth login (Email + Password)
4. After sign-in, the discovered tools will appear

<img src="databricks-images/04_marketplace_login.png" width="700" alt="Marketplace MCP Login">

> **Note:** After Marketplace installation, the MCP service is ready to use in AI Playground and Supervisor Agent. You can skip Section 8 (manual creation) and proceed to Section 9.
---

## 9. MCP Tools Available

After connecting, these tools are available from the MCP Gateway:

| Tool | Description |
|---|---|
| `normalize-ppml___normalize_ppml_term` | Normalize medical terms using IMO Precision Normalize API |
| `graphql-modifier___get_lexical` | Look up an IMO Problem lexical by its lexical code |
| `graphql-modifier___get_narrower_with_refinements` | Get narrower IMO lexicals filtered by refinement criteria |
| `graphql-modifier___get_refinement_group` | Look up all refinements within a refinement group |
| `ccp___entity_extraction` | Extract diagnosis entities from clinical notes |

### Tool Workflow

```
1. ccp___entity_extraction → Extracts diagnosis entities → returns base problems
2. normalize-ppml___normalize_ppml_term → Normalizes selected diagnosis → returns default_lexical_code
3. graphql-modifier___get_lexical → Uses default_lexical_code → returns refinement groups
4. graphql-modifier___get_refinement_group → Looks up refinement options within a group
5. graphql-modifier___get_narrower_with_refinements → Applies refinements → resolves most specific diagnosis
6. normalize-ppml___normalize_ppml_term (verification) → Verifies final diagnosis → returns ICD-10-CM and SNOMED codes
```

---

## 10. Validate MCP Connection in AI Playground

Before building the agent, validate that the MCP tools work.

### Step 11: Open AI Playground

1. Click **Playground** in the left sidebar (under AI/ML section)
2. Select a model from the dropdown (e.g., **Claude Opus 4.7**)
3. Click **Tools** → **+ Add tool**

<img src="databricks-images/08_ai_playground.png" width="700" alt="AI Playground">

### Step 12: Add MCP Tools

1. In the **Add tools** dialog, scroll to **UC Connection MCP Server** section
2. Click the **"Select a Unity Catalog Connection"** dropdown
3. Select **imo-health-mcp-gateway**
4. Click **Save**

<img src="databricks-images/09_add_mcp_tool.png" width="700" alt="Add MCP Tool - UC Connection">

### Step 13: Verify Tool is Connected

1. You should see **Tools (1)** in the top bar
2. Under MCP Servers, it shows: **UC Connection: imo-health-mcp-gateway**
3. You can also add a system prompt using **+ Add system prompt**

<img src="databricks-images/10_playground_connected.png" width="700" alt="Playground with MCP Connected">

### Step 14: Test the Connection

Type a test query in the chat:

```
What is the IMO lexical code for chest pain?
```

Verify the agent:
- Calls the normalize tool
- Returns the lexical code, ICD-10, and SNOMED CT codes
- Tools auto-execute without approval

<img src="databricks-images/10_playground_test.png" width="700" alt="Playground Test">

---

## 11. Create Supervisor Agent

### Step 15: Navigate to Agents

1. Click **Agents** in the left sidebar (under AI/ML section)
2. Click **Create Agent** button (top-right)
3. In the **"Create new Agent"** dialog, select **Supervisor Agent**

<img src="databricks-images/11_create_agent.png" width="700" alt="Create New Agent - Supervisor Agent">

### Step 16: Configure the Agent

After selecting Supervisor Agent, you will land on the Build page showing:
- **Tools and sub-agents** section (left panel) — with search bar to add tools
- **Instructions** and **Description** sections (collapsed)
- **Chat panel** (right side) — "What would you like to test?"

<img src="databricks-images/12_agent_build_page.png" width="700" alt="Supervisor Agent Build Page">

---

## 12. Agent Configuration

### Step 17: Add MCP Gateway as Tool

1. In the **Build** tab, under **Tools and sub-agents**
2. Click the **Search Databricks** box
3. Type **"mcp-gateway"**
4. Select **mcp-gateway** (UC Connection) from the results

<img src="databricks-images/13_add_mcp_tool.png" width="700" alt="Add MCP Tool to Agent">

### Step 18: Configure Agent Details

1. Click **Description** section to expand it
2. Fill in the description:

| Field | Value |
|---|---|
| Name | IMO-Diagnosis-Specificity-Agent |
| Description | Clinical diagnostic specificity agent that normalizes medical terms, traverses the IMO Knowledge Graph to find all refinement paths, and resolves the most specific diagnosis codes. Returns complete specificity matrices with IMO lexical codes, ICD-10-CM, and SNOMED CT mappings. |

<img src="databricks-images/14_agent_details.png" width="700" alt="Agent Details">

### Step 19: Add Agent Instructions

1. Click **Instructions** section to expand it
2. Paste your agent prompt:

```xml
<role>
You are an IMO Health clinical knowledge assistant that uses the IMO Knowledge Graph and
Normalize engine to provide specific, evidence-based answers to clinical terminology and
coding questions.
</role>

<capabilities>
- Find specific ICD-10-CM codes for clinical conditions
- Map diagnoses to the most specific codes available
- Identify diagnostic tests, findings, and treatments via the Knowledge Graph
- Suggest code specificity improvements with refinements
- Answer medical terminology questions using IMO lexicals
</capabilities>

<rules>
- Always call tools. Never guess or fabricate codes.
- Always give final response related to what user asked.
- If a term cannot be normalized, inform the user and suggest alternative terms.
- Always start from the broadest parent concept and traverse DOWN.
- Never normalize sub-conditions individually.
- When multiple specificity paths exist, show ALL paths from the graph traversal.
- Include IMO lexical codes in every result.
- Show the COMPLETE set of narrower concepts. Never truncate.
- Do not suggest next steps or recommendations at the end of the response.
- At the end of every response, generate 3-5 related sample questions the user can ask
  next. These should be contextually relevant to the current response and different each time.
</rules>
```

<img src="databricks-images/15_agent_instructions.png" width="700" alt="Agent Instructions">

---

## 13. Test Your Agent

### Step 20: Test in Build Tab

1. In the **Build** tab, use the chat panel on the right side
2. Type a test message in the **"Start typing ..."** box:

```
What are kidney complications associated with diabetes? Give me IMO lexicals for each.
```

3. The agent will ask for **tool approval** — click **Approve** for each tool call
4. Verify the agent returns structured results with lexical codes
5. You can also click **"Open in Playground"** (top-right) to test without tool approval

<img src="databricks-images/16_test_agent1.png" width="700" alt="Test Agent">

<img src="databricks-images/16_test_agent2.png" width="700" alt="Test Agent Response">

> **Note:** The Supervisor Agent always asks for tool approval in the Build UI. This is by design and cannot be disabled. Click **"Open in Playground"** to test with auto-execution.

---

## 14. Deploy as Serving Endpoint

### Step 21: Check Your Endpoint

The Supervisor Agent automatically creates a serving endpoint when you save.

1. Click **Endpoint** button (top-right of agent page, shows green dot when ready)
2. You will see the **Serving endpoints** page with endpoint name: `mas-d4d27a85-endpoint`
3. Verify status shows **Ready** (green checkmark)
4. Copy the endpoint URL

<img src="databricks-images/17_serving_endpoint.png" width="700" alt="Serving Endpoint">

### Endpoint Details

| Field | Value |
|---|---|
| Endpoint name | `mas-d4d27a85-endpoint` |
| Endpoint URL | `https://dbc-e7cb1d73-704e.cloud.databricks.com/serving-endpoints/mas-d4d27a85-endpoint/invocations` |
| Active configuration | `mas-base-model-9e60c0fe` (Supervisor Agent) |
| Status | Ready |
| Authentication | Bearer token required |

---

## 15. Generate Access Token

### Step 22: Generate Access Token

1. Click your **username** (top-right) → **Settings**
2. Click **Developer** in the left sidebar
3. Under **Access tokens**, click **Manage** or **Generate new token**
4. Name: `imo-agent-token`
5. Click **Generate** → Copy the token

<img src="databricks-images/18_generate_token.png" width="700" alt="Settings - Developer - Access Tokens">

> **Note:** If you see "Tokens are disabled for your organization", contact your workspace admin to enable personal access tokens or use Service Principal + OAuth for production.

---

## 16. Important Notes

### Tool Approval Behavior

| Environment | Tool Approval Required? |
|---|---|
| Agent Builder (Build tab) | Yes — always |
| AI Playground | No — auto-executes |
| Serving Endpoint (API) | Yes — needs approval loop |
| Deployed via Custom Agent | No — auto-executes |

### Token Management

| Token Type | Best For | Lifetime |
|---|---|---|
| Personal Access Token (PAT) | Development/testing | Configurable (days) |
| Service Principal + OAuth | Production | Auto-refreshes (1 hour) |

> For production, ask your workspace admin to create a Service Principal.

---

## 17. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| 401 Unauthorized | Token missing or expired | Generate new token in Developer settings |
| Empty response | Wrong request format | Use `{"input": [...]}` not `{"messages": [...]}` |
| `mcp_approval_request` in response | Supervisor Agent behavior | Use auto-approve wrapper code |
| MCP tools not visible | Not authenticated to MCP | Click Login on MCP Service detail page |
| Connection fails | OAuth credentials invalid | Verify Client ID/Secret with IMO team |
| Endpoint not ready | Still deploying | Wait 10-15 minutes, check status |
| Raw JSON in response | Build UI shows tool output | Normal in Build UI; API returns only text |

---

## 18. Quick Reference

| Step | Action | Where |
|---|---|---|
| 1 | Create HTTP Connection | Catalog → Connections |
| 2 | Register MCP Service | AI Gateway → MCPs → Register |
| 3 | Authenticate MCP | MCP Service → Login |
| 4 | Validate in Playground | AI Playground → Add MCP tool → Test |
| 5 | Create Supervisor Agent | Agents → + Create → Supervisor |
| 6 | Add MCP tool to agent | Build tab → Tools and sub-agents |
| 7 | Add instructions | Build tab → Instructions |
| 8 | Test | Build tab → Chat panel |
| 9 | Deploy | Automatic (endpoint created on save) |
| 10 | Generate token | Settings → Developer → Access tokens |
| 11 | Call via API | POST to endpoint URL with Bearer token |

---

## Version History

| Date | Version | Change |
|---|---|---|
| 2026-07-08 | 1.0 | Initial Databricks Supervisor Agent build guide |
