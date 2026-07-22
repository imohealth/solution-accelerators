# IMO Health Diagnosis Specificity Agent

Complete Build Guide - Microsoft Copilot Studio (New Experience)

End-to-end guide to build, configure, and publish the IMO Diagnosis Specificity Agent using Microsoft Copilot Studio's new experience UI.

---

## 1. About IMO Health

IMO (Intelligent Medical Objects) Health provides clinical terminology and mapping solutions for healthcare. IMO APIs help normalize medical terms and traverse knowledge graphs to find the most specific diagnosis codes (ICD-10).

---

## 2. About Microsoft Copilot Studio (New Experience)

The new Copilot Studio experience is an instructions-driven, AI-first platform for building agents. Key differences from the classic experience:

- Instructions-first authoring — describe what the agent should do in natural language
- Unified Build tab — all configuration in one place (Instructions, Tools, Knowledge, Model)
- Enhanced orchestration — agent automatically decides when to use tools based on context
- Built-in evaluation — Preview, Evaluate, and Monitor tabs for quality assurance
- Auto tool discovery — MCP tools are automatically available without manual enable/disable

---

## 3. Prerequisites

Before you start, make sure you have:

| Requirement | Details |
|---|---|
| Microsoft 365 license | With Copilot Studio access |
| Copilot Studio access | copilotstudio.microsoft.com |
| IMO Health MCP Gateway URL | Provided by IMO team |
| IMO Auth Details | Client ID, Client Secret, Auth URLs (provided by IMO team) |
| Browser | Edge or Chrome (latest) |

---

## 4. Purpose of This Guide

This guide walks you through building a Clinical Diagnostic Specificity Agent in Copilot Studio (new experience) that finds the most specific diagnosis for a patient visit using the IMO Knowledge Graph. The agent connects to IMO APIs via an MCP (Model Context Protocol) server. This serves as a guide for anyone who wants to build an Agent using the capabilities of the IMO MCP server on the Copilot Studio platform.

---

## 5. Login to Copilot Studio

### Step 1: Open Copilot Studio

1. Go to `https://copilotstudio.microsoft.com`
2. Sign in with your Microsoft 365 account
3. You will land on the Home page

> **Note:** To sign in to Microsoft Copilot Studio, you need a **work or school Microsoft account**. Personal Microsoft accounts (e.g., @outlook.com, @hotmail.com) are not supported.

<img src="copilotstudio-new-images/copilotstudio-new-images/01_copilot_studio_home.png" width="700" alt="Copilot Studio Home Page">

### Step 2: Switch to New Experience (if needed)

1. If you see a banner at the top saying **"Try the new experience"**, click it
2. Or toggle the experience switch in the top navigation
3. You should now see the new UI with the unified Build surface

---

## 6. Create a New Agent

<img src="copilotstudio-new-images/copilotstudio-new-images/02_new_experience_create.png" width="700" alt="New Experience - Create Agent">

### Step 3: Create Agent

1. Click **"+ Create"** or **"Create new agent"** from the Home page
2. Enter a brief description of what your agent should do
3. The AI will generate suggestions for name, description, and instructions

<img src="copilotstudio-new-images/copilotstudio-new-images/03_create_agent.png" width="700" alt="Create New Agent">

### Step 4: Agent Build Tab

After creation, you will land on the **Build** tab with:
- Left side — Instructions editor (agent name, icon, instructions text)
- Right side — Components Panel (Model, Tools, Knowledge, Skills, etc.)

<img src="copilotstudio-new-images/copilotstudio-new-images/04_build_tab_overview.png" width="700" alt="Build Tab Overview">

---

## 7. Agent Configuration

### Step 5: Set Agent Name and Description

1. In the Build tab, click on the agent name at the top to edit it
2. Set the name: `IMO Health Diagnosis Specificity Agent`

<img src="copilotstudio-new-images/copilotstudio-new-images/05_agent_name.png" width="700" alt="Agent Name">

### Step 6: Add Agent Instructions

1. In the **Instructions** editor (left side of Build tab)
2. Paste the following prompt:

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

<img src="copilotstudio-new-images/copilotstudio-new-images/06_agent_instructions.png" width="700" alt="Agent Instructions">

### Step 7: Select Model

1. In the **Components Panel** (right side), click **Model**
2. Select your preferred LLM model (e.g., GPT-4o, Claude, etc.)
3. Click **Save**

<img src="copilotstudio-new-images/copilotstudio-new-images/07_model_selection.png" width="700" alt="Model Selection">

---

## 8. Add IMO MCP as a Tool

### What is MCP?

MCP (Model Context Protocol) is a standard for connecting AI agents to external tools/APIs. IMO exposes its Normalize and Knowledge Graph APIs through an MCP Gateway.

```
Copilot Studio Agent (Instructions) → MCP Gateway Server → IMO APIs
```

### Step 8: Navigate to Tools

1. In the **Components Panel** (right side), click **Tools**
2. Click **"+ Add a tool"**

<img src="copilotstudio-new-images/copilotstudio-new-images/08_tools_panel.png" width="700" alt="Tools Panel">

### Step 9: Add MCP Server

1. In the **Add a tool** dialog, select **"Model Context Protocol (MCP)"**
2. Fill in the MCP Server details:

| Field | Value |
|---|---|
| Server Name | mcp-gateway |
| Server Description | IMO Health MCP Gateway for clinical terminology |
| Server URL | `https://api.imohealth.com/mcp` |
| Authentication | OAuth 2.0 |

3. Click **Add**

<img src="copilotstudio-new-images/copilotstudio-new-images/09_add_mcp_server.png" width="700" alt="Add MCP Server">

### Step 10: Configure OAuth 2.0 Authentication

| Field | Value |
|---|---|
| Client ID | (provided by IMO team) |
| Client Secret | (provided by IMO team) |
| Authorization URL | (provided by IMO team) |
| Token URL | (provided by IMO team) |
| Scopes | (provided by IMO team) |

<img src="copilotstudio-new-images/copilotstudio-new-images/10_oauth_config.png" width="700" alt="OAuth Configuration">

### Step 11: Authenticate with IMO Health

1. After adding the MCP server, click **Login** or **Connect**
2. The IMO Health login page will appear
3. Enter your **Email** and **Password**
4. Click **LOGIN**
5. This completes the OAuth authentication

<img src="copilotstudio-new-images/copilotstudio-new-images/11_imo_health_login.png" width="700" alt="IMO Health Login">

> **Note:** In the new experience, tools from the MCP server are automatically discovered and available to the agent. No manual enable/disable needed.

---

## 9. MCP Tools Available

After connecting, these tools are automatically available from the MCP Gateway:

| Tool | Description |
|---|---|
| `mcp__imo-health__categorize___categorize_problems` | Categorize medical problems |
| `mcp__imo-health__ccp___entity_extraction` | Extract clinical entities from text |
| `mcp__imo-health__core-search___get_term_detail` | Get details for a specific term |
| `mcp__imo-health__core-search___lookup_term_by_code` | Look up a term by its code |
| `mcp__imo-health__core-search___search_medical_term` | Search for medical terms |
| `mcp__imo-health__graphql-modifier___get_allowed_refinements` | Get allowed refinements for a term |
| `mcp__imo-health__graphql-modifier___get_cross_domain` | Get cross-domain mappings |
| `mcp__imo-health__graphql-modifier___get_lexical` | Get lexical information |
| `mcp__imo-health__graphql-modifier___get_mappings` | Get term mappings |
| `mcp__imo-health__graphql-modifier___get_narrower_hierarchy` | Get narrower hierarchy |
| `mcp__imo-health__graphql-modifier___get_narrower_sequential_refinements` | Get narrower sequential refinements |
| `mcp__imo-health__graphql-modifier___get_narrower_with_refinements` | Get narrower terms with refinements |
| `mcp__imo-health__graphql-modifier___get_refinement_group` | Get refinement groups |
| `mcp__imo-health__graphql-modifier___get_related_problems` | Get related problems |
| `mcp__imo-health__normalize-ppml___normalize_ppml_term` | Normalize a term using PPML |

### Tool Workflow

```
1. ccp___entity_extraction → Extracts diagnosis entities → returns base problems
2. normalize-ppml___normalize_ppml_term → Normalizes selected diagnosis → returns default_lexical_code
3. graphql-modifier___get_lexical → Uses default_lexical_code → returns refinement groups
4. graphql-modifier___get_refinement_group → Looks up refinement options within a group
5. graphql-modifier___get_narrower_with_refinements → Applies refinements → resolves most specific diagnosis
6. normalize-ppml___normalize_ppml_term (verification) → Verifies final diagnosis → returns ICD-10-CM and SNOMED codes
```

> **Note:** The enhanced orchestration automatically decides when to call each tool based on the user's query and your instructions. No manual trigger configuration needed.

---

## 10. Test Your Agent

### Step 12: Use Preview Tab

1. Click the **Preview** tab (top navigation)
2. Type a test message:

```
What are the specificity paths for chest pain?
```

3. Verify the agent:
   - Calls the MCP tools automatically
   - Returns structured results with lexical codes and ICD-10 codes
   - Suggests follow-up questions at the end

<img src="copilotstudio-new-images/copilotstudio-new-images/12_preview_test.png" width="700" alt="Preview Test">

### Step 13: Verify Tool Calls

1. Check that the agent is calling the correct tools
2. You should see tool invocations in the response flow
3. Verify results contain IMO lexical codes

<img src="copilotstudio-new-images/copilotstudio-new-images/13_tool_calls.png" width="700" alt="Tool Calls Verification">

---

## 11. Publish Your Agent

### Step 14: Publish

1. Click **Publish** in the top menu bar
2. Review the summary
3. Click **Publish** to confirm
4. Wait for the status to show published (green banner)

<img src="copilotstudio-new-images/copilotstudio-new-images/14_publish.png" width="700" alt="Publish Agent">

---

## 12. Configure Channels

### Step 15: Add Teams Channel

1. After publishing, click **Channels** in the top menu bar
2. Select **Teams and Microsoft 365 Copilot**
3. Authentication is automatically set to Microsoft Entra ID for Teams
4. Click **Save**

<img src="copilotstudio-new-images/copilotstudio-new-images/15_channels_teams.png" width="700" alt="Teams Channel">

### Step 16: Make Agent Available

1. Click **"Make the agent available to others"**
2. Choose availability:
   - Show to my teammates — for testing
   - Show to everyone in the organization — for org-wide deployment
3. Share the installation link or submit for admin approval

---

## 13. How Users Access the Agent

### In Microsoft Teams

1. Open Microsoft Teams
2. Click **Chat** in the left sidebar
3. Click **New chat** or search for the agent name
4. Type: **IMO Health Diagnosis Specificity Agent**
5. Select it from the results
6. Start chatting with your clinical query

### In Microsoft 365 Copilot

1. Open Microsoft 365 Copilot
2. Find the agent in the Agent Store
3. Click to start a conversation

---

## 14. Important Notes

### New Experience vs Classic

| Feature | New Experience | Classic Experience |
|---|---|---|
| Authoring | Natural language instructions | Topic-based with triggers |
| Tools | Auto-available, agent decides when to use | Manual enable/disable per tool |
| Orchestration | Enhanced (always on) | Classic or generative (configurable) |
| Testing | Preview + Evaluate + Monitor tabs | Test panel only |
| MCP tools | Auto-discovered after connection | Manual toggle per tool |

### Key Points

- Tools are **automatically available** once the MCP server is connected — no manual enable/disable needed
- The agent uses **enhanced orchestration** to decide when to call tools based on context
- **No migration path** between old and new experience — agents are separate
- Publishing applies to **all connected channels** simultaneously
- In Teams, users get updates after starting a new session (type `start over` for immediate update)

---

## 15. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Agent not using tools | Instructions not clear enough | Make instructions more specific about when to call tools |
| MCP connection fails | OAuth credentials invalid | Verify Client ID/Secret with IMO team |
| Tools not appearing | MCP server not connected | Check Tools section in Components Panel |
| Agent in old experience | Not switched to new UI | Toggle "New experience" at the top |
| Works in Preview but not Teams | Not published | Click Publish after making changes |
| Slow responses | Multiple sequential tool calls | Expected behavior (5-6 tool calls) |
| Agent not appearing in Teams | Not yet approved | Wait 10-15 min, refresh Teams |

---

## 16. Quick Reference

| Step | Action | Where |
|---|---|---|
| 1 | Create agent | Home → + Create |
| 2 | Add instructions | Build tab → Instructions editor |
| 3 | Select model | Build tab → Components → Model |
| 4 | Add MCP server | Build tab → Components → Tools → + Add → MCP |
| 5 | Authenticate | MCP server → Login with IMO credentials |
| 6 | Test | Preview tab → Type query |
| 7 | Publish | Top menu → Publish |
| 8 | Add channel | Top menu → Channels → Teams |

---

## Version History

| Date | Version | Change |
|---|---|---|
| 2026-07-09 | 1.0 | Initial Copilot Studio (New Experience) build guide |
