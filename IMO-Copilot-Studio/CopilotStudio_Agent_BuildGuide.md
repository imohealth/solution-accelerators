# IMO Health Diagnosis Specificity Agent — Complete Build and Publish Guide

End-to-end guide to build, configure, and publish the IMO Health Diagnosis Specificity Agent using Microsoft Copilot Studio.

---

## 1. About IMO Health

IMO (Intelligent Medical Objects) Health provides clinical terminology and mapping solutions for healthcare. IMO APIs help normalize medical terms and traverse knowledge graphs to find the most specific diagnosis codes (ICD-10).

---

## 2. About Microsoft Copilot Studio

Microsoft Copilot Studio is a low-code platform to build, test, and publish AI agents. It supports:

- Custom instructions (system prompts)
- External tool/API integration
- Multi-channel publishing (Teams, Web, Slack, etc.)
- Built-in authentication and analytics

---

## 3. Prerequisites

Before you start, make sure you have:

| Requirement | Details |
|---|---|
| Microsoft 365 license | With Copilot Studio access |
| Copilot Studio access | copilotstudio.microsoft.com |
| IMO Health MCP Gateway URL | Provided by IMO team |
| Auth Details | For MCP Gateway authentication |
| Browser | Edge or Chrome (latest) |

---

## 4. Purpose of This Guide

This guide walks you through building a **Clinical Diagnostic Specificity Agent** in Copilot Studio that finds the most specific diagnosis for a patient visit using the IMO Knowledge Graph. This uses the IMO MCP server to power the output of the Agent. This is to serve as a guide for anyone who wants to build an Agent using the capabilities of the IMO MCP server, and the following is just one use case with the IMO MCP server.

### What the Agent Does

1. User pastes a clinical note or encounter summary
2. Agent extracts clinical findings from the note
3. User picks a finding to refine
4. Agent searches IMO, queries the Knowledge Graph for refinements, and reasons about which refinements match the clinical evidence
5. Agent recommends the most specific diagnosis with full transparency

---

## 5. Agent Architecture

### Overview

The IMO Health Diagnosis Specificity Agent is an instruction-based Copilot Studio agent that connects to IMO APIs via an MCP (Model Context Protocol) server.

```
Copilot Studio Agent (Instructions) --> MCP Gateway Server --> IMO APIs
```

### MCP Server Configuration

| Setting | Value |
|---|---|
| Server Name | mcp-gateway |
| Connection Name | mcp-gateway |
| Status | Enabled |
| Available to | IMO Health Diagnosis Specificity Agent |

### MCP Tools (Enabled)

The agent uses the following tools from the mcp-gateway server:

| Tool | Description |
|---|---|
| `ccp___entity_extraction` | Extract diagnosis entities from clinical notes using IMO Entity Extraction API. Returns entities with semantic type, assertion status, and code mappings. |
| `normalize-ppml___normalize_ppml_term` | Normalize medical terms using the IMO Precision Normalize API. Send one or more medical terms and receive standardized results. |
| `graphql-modifier___get_lexical` | Look up an IMO Problem lexical in the IMO Health Knowledge Graph by its lexical code. |
| `graphql-modifier___get_narrower_with_refinements` | Get narrower IMO lexicals filtered by specific refinement criteria. Uses the `lexical_code` value from normalization. |
| `graphql-modifier___get_refinement_group` | Look up all refinements within a specific refinement group. Returns the group title and all available refinement options. |

### Tool Workflow

```
1. ccp___entity_extraction
   --> Extracts diagnosis entities from clinical note --> returns base problems

2. normalize-ppml___normalize_ppml_term
   --> Normalizes selected base diagnosis --> returns default_lexical_code

3. graphql-modifier___get_lexical
   --> Uses default_lexical_code --> returns refinement groups

4. graphql-modifier___get_refinement_group
   --> Looks up refinement options within a specific group

5. graphql-modifier___get_narrower_with_refinements
   --> Applies supported refinements --> resolves most specific diagnosis

6. normalize-ppml___normalize_ppml_term (verification)
   --> Verifies final diagnosis --> returns ICD-10-CM and SNOMED codes
```

---

## 6. Create Your Agent in Copilot Studio

### Step 1: Open Copilot Studio

1. Go to copilotstudio.microsoft.com
2. Sign in with your Microsoft 365 account
3. You will land on the **Home** page

<img src="images/01_copilot_studio_home.png" width="700" alt="Copilot Studio Home Page">

### Step 2: Create a New Agent

1. Click **"+ Agent"** in the left sidebar
2. Select **"New agent"**
3. Fill in:
   - **Name:** Provide name to agent
   - **Description:** Describe what agent does and specify purpose
   - **Instructions:** Provide agent prompt
   - **Model:** Choose LLM Model
4. Click **"Create"**

<img src="images/02_create_new_agent.png" width="700" alt="Create New Agent Dialog">

### Step 3: Agent Overview

After creation, you land on the agent overview page. From here you can:

- Edit instructions
- Add tools (actions)
- Test the agent
- Publish

<img src="images/03_agent_overview.png" width="700" alt="Agent Overview Page">

---

## 7. Agent Configuration

### a] Agent Name

```
IMO Health Diagnosis Specificity Agent
```

### b] Agent Description

```
IMO Health Diagnosis Specificity Agent analyzes clinical notes to extract diagnoses and refine
them to maximum specificity using the IMO Knowledge Graph. Provides evidence-based refinements
with ICD-10 and SNOMED CT codes for accurate clinical documentation and billing.
```

### c] Model

```
Claude Opus 4.8
```

### d] Agent Prompt (Instructions)

Paste the following into the **Instructions** field:

```
You are a clinical diagnostic specificity agent that uses IMO Normalize and the IMO Knowledge
Graph to find the most specific diagnosis supported by the clinical note.

Your greeting is already shown. Do not repeat it unless asked.

GOAL
Work end to end from conversation context:
1. Read the clinical note
2. Extract base problems using entity extraction
3. Identify the diagnosis to refine
4. Normalize the base diagnosis
5. Retrieve allowed refinements
6. Match refinements to note evidence
7. Resolve the most specific diagnosis
8. Verify final coding
9. Present the result clearly

Use only conversation context:
- the most recent clinical note
- the most recently selected or explicitly named diagnosis

COMMUNICATION RULES
Before each important action, briefly explain what you are doing and why.

ENTRY RULES
1. If there is a clinical note but no diagnosis selected:
   - Extract base problems only
   - Do not call tools
   - Ask which diagnosis should be refined
   - Stop

2. If the clinical note and diagnosis to refine are already clear:
   - Treat this as a refinement request
   - Start refinement immediately

3. If the user directly asks to refine a diagnosis:
   - Start refinement immediately

If either the clinical note or diagnosis is missing, ask only for the missing piece and stop.

CRITICAL RULES
1. For every refinement request, always use live tool calls.
2. Use default_lexical_code, never lexical_code, when calling
   graphql-modifier___get_lexical.
3. Select only refinements supported by the clinical note.
4. Never select unspecified, other, NOS, or similar default refinements.
5. Never invent evidence, diagnoses, refinement support, or codes.
6. Summarize tool outputs in tables, not raw payloads.

PHASE 1: EXTRACT THE BASE PROBLEM (TEXT ONLY -- NO TOOL CALLS)

When the user provides a clinical note or encounter summary:

Case A -- User explicitly names a diagnosis to refine (e.g., "find most specific diagnosis
for diabetes", "refine hypertension"):
- The user has already told you what to refine. Do NOT list findings or ask.
- Skip directly to Phase 2 using the diagnosis the user mentioned.
- Proceed through Phase 2 --> 3 --> 4 in one continuous flow.

Case B -- User provides a clinical note (DEFAULT CASE):
- Read the entire note carefully -- look at History, HPI, Assessment, and Plan sections.
- EXTRACTION RULES:
  1. Single-disease follow-up (Chief Complaint names one disease): extract ONLY that disease
     -- ignore complications, associated conditions, and sub-numbered Assessment items.
  2. Multi-disease note: extract only top-level numbered Assessment items -- nested sub-items
     belong to their parent.
  3. Crisis/acute episode: extract ONLY the underlying disease, not the crisis type
     (e.g., "Sickle Cell Crisis with Acute Chest Syndrome and VOC" --> "Sickle cell anemia").
  4. Splitting: two INDEPENDENT diseases combined --> split
     (e.g., "Hypertensive CKD" --> "Hypertension" + "Chronic kidney disease").
     Disease + its own complication --> keep as one
     (e.g., "Type 2 diabetes with retinopathy" --> "Diabetes mellitus").
- Examples:
  - "Type 2 diabetes with diabetic peripheral neuropathy" --> "Diabetes mellitus"
  - "Hypertensive chronic kidney disease with stage 3 CKD" --> "Hypertension" AND
    "Chronic kidney disease"
  - "Sickle Cell Crisis with Acute Chest Syndrome and VOC" --> "Sickle cell anemia"
- OUTPUT: Numbered list of base diagnosis names ONLY. No qualifiers, no explanations,
  no parenthetical info.
  - Correct: "1. Nasal congestion"
  - Wrong: "1. Nasal congestion (from fall pollen and allergies)"

Ask: Please specify which finding you would like to refine.
Stop. Do not proceed until the user selects a diagnosis.

- Extract ONLY diagnoses that appear in the Assessment/Impression section.
  Do NOT extract conditions mentioned only in HPI as patient background.
  Do NOT extract symptoms, signs, vitals, or lab values as separate findings.
- Extract ONLY the base diagnoses/conditions -- strip away ALL qualifiers such as
  severity, laterality, anatomical location details, chronicity, typing, and
  associated conditions.

PHASE 2: IDENTIFY ACTIVE NOTE AND DIAGNOSIS
Use the most recent clinical note and most recently selected or explicitly named diagnosis.
If either is missing, ask only for the missing piece and stop.

PHASE 3: NORMALIZE THE BASE DIAGNOSIS
Call normalize-ppml___normalize_ppml_term with:
- domain = "Problem"
- number_of_results = 1

Extract: preferred title, default_lexical_code, ICD-10-CM codes, SNOMED codes if available.

Show:
#### Normalization Result
| Selected Diagnosis | Normalized Term | IMO Lexical Code | Base ICD-10-CM Codes | SNOMED CT Codes |
|---|---|---|---|---|
| [selected diagnosis] | [preferred title] | [default_lexical_code] | [codes] | [codes or "None"] |

PHASE 4: GET ALLOWED REFINEMENTS
Call graphql-modifier___get_lexical with default_lexical_code.

Show:
#### Allowed Refinements from Knowledge Graph
| Refinement Group | Allowed Refinements |
|---|---|
| [group name] | [comma-separated refinement titles] |

Show titles only. Do not select refinements yet.

PHASE 5: MATCH REFINEMENTS TO NOTE EVIDENCE
Inform the user that you are comparing refinement options with the clinical note so only
evidence-supported choices are kept.

For each refinement group:
- Review the note for direct evidence or clear implication
- Select only supported refinements
- If none is supported, mark the group as an evidence gap

Show:
#### Refinement Analysis
| Refinement Group | Selected Refinement | Evidence from Note | Reasoning |
|---|---|---|---|
| [group] | [selected or "No evidence"] | [quote or evidence] | [why selected or rejected] |

PHASE 6: RESOLVE THE MOST SPECIFIC DIAGNOSIS
Inform the user that you are resolving the most specific diagnosis that matches the
supported refinements.

Call graphql-modifier___get_narrower_with_refinements with the base lexical code
and supported refinement codes.
- Use one option per refinement group in each call
- If multiple supported combinations exist, test each valid combination separately
- Include every valid resolved path
- If no refinements are supported, use an empty refinement list only if needed

The base diagnosis must remain part of the final diagnosis.

Show:
#### Resolved Diagnosis Paths
| Path | Refined Diagnosis | IMO Lexical Code | Applied Refinements |
|---|---|---|---|
| 1 | [resolved diagnosis] | [code] | [comma-separated refinements] |

PHASE 7: VERIFY FINAL CODING
Inform the user that you are verifying the final diagnosis with Normalize to confirm the
standardized title and ICD-10-CM codes.

Call normalize-ppml___normalize_ppml_term again on each final resolved diagnosis title.

Show:
#### Final Coding Verification
| Refined Diagnosis | Refined ICD-10-CM Codes | SNOMED CT Codes |
|---|---|---|
| [resolved diagnosis] | [codes] | [codes or "None"] |

OUTPUT ORDER:
1. Normalization Result
2. Allowed Refinements from Knowledge Graph
3. Refinement Analysis
4. Resolved Diagnosis Paths
5. Final Coding Verification
6. Final Recommendation

#### Final Recommendation
- Base Diagnosis: [base diagnosis]
- Base ICD-10-CM Codes: [comma-separated base codes]
- Most Specific Diagnosis: [best resolved diagnosis]
- Refined ICD-10-CM Codes: [comma-separated refined codes]
- IMO Lexical Code: [final code]
- Evidence Summary: [In brief]
- Evidence Gaps: [In brief]
```

<img src="images/04_instructions_editor.png" width="700" alt="Instructions Editor with Prompt">

---

## 8. Add IMO MCP as a Tool

### What is MCP?

MCP (Model Context Protocol) is a standard for connecting AI agents to external tools/APIs. IMO exposes its Normalize and Knowledge Graph APIs through an MCP Gateway.

### Step 4: Navigate to Tools

1. In your agent, click **"Tool"** in the left menu

<img src="images/05_tools_menu.png" width="700" alt="Tools Menu in Agent">

2. Click **"+ Add an action"**
3. Click **"Model Context Protocol (MCP)"**

<img src="images/06_add_tool_dialog.png" width="700" alt="Add Tool Dialog - Featured Tab">

<img src="images/07_add_mcp_tool.png" width="700" alt="Add Tool Dialog - MCP Tab">

4. Click **"+ Add"**

### Step 5: Fill the MCP Server Details

| Field | Value |
|---|---|
| Server Name | mcp-gateway |
| Server Description | mcp gateway in imo health for mcp usage |
| Server URL | https://api.imohealth.com/mcp |
| Authentication | OAuth 2.0 |

### Step 6: Configure OAuth 2.0 Authentication

| Field | Value |
|---|---|
| Type | Manual |
| Client ID | (provided by IMO team) |
| Client Secret | (provided by IMO team) |
| Authorization URL | (provided by IMO team) |
| Token URL Template | (provided by IMO team) |
| Refresh URL | (provided by IMO team) |
| Scopes | (provided by IMO team) |
| Redirect URL | (auto-generated after saving) |
| Note | Add Redirect URL to Auth0 Allowed Callback URLs |

<img src="images/08_mcp_server_config.png" width="700" alt="MCP Server Configuration with OAuth">

### Step 7: Enable Required Tools

After connecting the MCP server, enable these 5 tools:

1. `ccp___entity_extraction`
2. `normalize-ppml___normalize_ppml_term`
3. `graphql-modifier___get_lexical`
4. `graphql-modifier___get_narrower_with_refinements`
5. `graphql-modifier___get_refinement_group`

Go to **Tools --> mcp-gateway --> Tools** and toggle each tool to **Enabled** (blue toggle).

<img src="images/09_tools_enabled.png" width="700" alt="Tools Enabled List">

---

## 9. Test Your Agent

### Step 8: Use the Test Panel

1. Click **"Test"** button (bottom-right chat panel)
2. Type a test message:
   ```
   Patient presents with chest pain radiating to left arm
   ```
3. Verify the agent:
   - Extracts base problems
   - Calls Normalize tool
   - Calls Knowledge Graph tool
   - Returns specific diagnosis with ICD-10 codes
4. Check **Activity** tab to confirm MCP tool calls are executing (not Knowledge search fallback)

<img src="images/10_test_panel.png" width="700" alt="Test Panel with Response">

---

## 10. Publish Your Agent

### Step 9: Publish

1. Click **"Publish"** button (top-right)
2. Review the summary
3. Click **"Publish"** to confirm
4. Wait for the status to show **"Published"**

<img src="images/10_test_panel.png" width="700" alt="Publish - See Published status in Test panel">

---

## 11. Deploy to Channels

### Available Channels

| Channel Type | Options |
|---|---|
| Share a preview | Demo website |
| Microsoft channels | Microsoft 365 and Microsoft Teams, SharePoint |
| Other channels | Web app, Native app, Facebook, WhatsApp, Twilio, Line, GroupMe, Direct Line Speech |

> **Note:** When using Microsoft authentication, only Teams, Microsoft 365, and SharePoint channels are available.

---

### Option A: Deploy to Microsoft Teams (Internal Users)

#### Configure Authentication

1. Open your agent in **Copilot Studio**
2. Go to **Settings --> Security --> Authentication**
3. Select **"Authenticate with Microsoft"** (Entra ID)
4. Save

#### Configure Teams Channel

1. Go to **Channels** tab in your agent
2. Click **Microsoft Teams**
3. Toggle **"Enable Teams"** to On
4. Click **"Open availability options"**
5. Choose availability:
   - **Show to my teammates and shared users** -- limited internal rollout
   - **Show to everyone in my organization** -- org-wide deployment
6. Save

#### Make Available in Teams

1. After publishing, go to **Channels --> Microsoft Teams**
2. Click **"Open in Teams"** to test
3. For org-wide distribution:
   - Click **"Submit for admin approval"**
   - The Teams admin will review and approve in **Teams Admin Center --> Manage apps**
4. Once approved, users find the agent in Teams app store under **"Built for your org"**

#### Verify in Teams

1. Open Microsoft Teams
2. Go to **Apps --> Built for your org** (or search for "IMO Health Diagnosis Specificity Agent")
3. Install the agent
4. Start a conversation and test the full workflow
5. Verify MCP tools are executing (not falling back to Knowledge search)

<img src="images/11_agent_in_teams.png" width="700" alt="Agent in Microsoft Teams">

---

### Option B: Deploy to Microsoft 365 and Microsoft Teams

The "Microsoft 365 and Microsoft Teams" channel handles both Copilot and Teams publishing in one place.

#### Open Channel Configuration

1. In Copilot Studio, go to **Channels** tab
2. Click **"Microsoft 365 and Microsoft Teams"** under Microsoft channels
3. This opens the channel configuration panel

#### Enable Microsoft 365 Copilot

1. Under **Microsoft 365 Copilot** section, check **"Make available in Microsoft 365 Copilot"**
2. This publishes the agent to the Agent Store inside Microsoft 365 Copilot
3. Once published, the agent is discoverable in Microsoft 365 workflows (Teams, Word, Excel, PowerPoint, Outlook)

#### Enable Microsoft Teams

1. Under **Microsoft Teams** section, the agent is available directly in chats, meetings, and channels
2. Users can find and use the agent inside Teams once it's shared or approved by admins

#### Configure Availability and Details

1. Click **"Availability options"** to set who can access the agent:
   - **Show to my teammates and shared users** -- limited internal rollout
   - **Show to everyone in my organization** -- org-wide deployment
2. Click **"Edit details"** in the Agent preview section to configure:
   - Agent name: IMO Health Diagnosis Specificity Agent
   - Description: Built using Microsoft Copilot Studio
   - Icons and branding
3. Click **Save**

#### Preview and Verify

- Click **"See in Microsoft 365"** -- opens the agent in Microsoft 365 Copilot
- Click **"See in Teams"** -- opens the agent in Microsoft Teams

#### Admin Approval (for org-wide access)

1. Click **"Submit for admin approval"** if deploying org-wide
2. The Teams/M365 admin reviews and approves in:
   - **Teams Admin Center --> Manage apps** (for Teams)
   - **Microsoft 365 Admin Center --> Integrated Apps** (for M365 Copilot)
3. Once approved, users can find the agent in the Agent Store or Teams app store

<img src="images/12_agent_in_m365.png" width="700" alt="Agent in Microsoft 365 Copilot">

---

### Option C: Deploy to Microsoft Marketplace (Client Distribution)

#### Prerequisites for Marketplace

- Microsoft Partner Center account (partner.microsoft.com)
- Verified publisher identity
- Agent meets Microsoft certification requirements
- Privacy policy URL
- Terms of use URL
- Support documentation

#### Prepare Agent for Multi-Tenant Access

1. In Copilot Studio, go to **Settings --> Security --> Authentication**
2. Enable **"Multi-tenant support"** (Preview)
3. Save -- this allows the agent to be accessed outside your tenant

#### Prepare Submission Package

| Item | Description |
|---|---|
| App name | IMO Health Diagnosis Specificity Agent |
| Short description | AI-powered clinical coding assistant for diagnostic specificity |
| Long description | Full description of capabilities and workflow |
| Icons | Color icon (192x192) and outline icon (32x32) |
| Screenshots | At least 2 screenshots showing the agent in action |
| Privacy policy | URL to published privacy policy |
| Terms of use | URL to published terms of use |
| Support URL | URL for client support |
| Publisher info | IMO Health verified publisher details |

#### Submit via Partner Center

1. Go to **partner.microsoft.com --> Marketplace offers**
2. Click **"New offer" --> Microsoft Teams app** (or Copilot agent)
3. Fill in:
   - **Offer setup** -- name, description, categories (Healthcare)
   - **Properties** -- app category, industries, support links
   - **Offer listing** -- descriptions, screenshots, videos
   - **Availability** -- pricing (free/paid), markets, visibility
   - **Technical configuration** -- link to your Copilot Studio agent
4. Click **"Review and publish"**

#### Microsoft Certification Review

- Microsoft reviews the submission (typically 3-7 business days)
- They validate: functionality, security, accessibility, content policies
- You may receive feedback requiring changes
- Once approved, the agent appears in the Marketplace

#### Client Installation

Once published to Marketplace, clients can:
1. Find the agent in **Microsoft AppSource** or **Teams App Store**
2. Install it in their tenant (requires their Teams admin approval)
3. Configure any required connections (MCP authentication)
4. Start using the agent

---

## 12. MCP Gateway Authentication for Published Agents

### The Problem

The MCP Gateway connection authenticated under your maker session in test mode may not carry over to the published agent. The published bot runs under its own service identity.

**Symptoms:**
- Agent shows "Search sources --> Knowledge" in Activity instead of tool calls
- Error: "No usable lexical code returned"
- Tools work in test pane but fail in published Teams channel

### Verify MCP Connection

1. Go to **Copilot Studio --> Your Agent --> Tools** tab
2. Click on **mcp-gateway** (the server)
3. Go to **Details** section
4. Verify:
   - **Server**: `mcp-gateway` shows connected
   - **Connection**: `mcp-gateway` shows green indicator (connected)
5. If connection shows warning/error:
   - Click on the connection
   - Re-authenticate or reconfigure with service-level credentials
   - Ensure the MCP Gateway URL is accessible from the published agent

### Authentication Configuration

| Setting | Value |
|---|---|
| Auth Type | OAuth 2.0 |
| Authority URL | https://auth.imohealth.com |
| Client ID | Registered app client ID |
| Client Secret | Stored in connection reference |
| Scope | As required by MCP Gateway |

Ensure the connection reference is:
- Configured at the **agent level** (not your personal session)
- Shared with the bot's service identity
- Valid and not expired

### Verify MCP Tools After Publishing

1. Test in Teams after publish
2. Go to **Activity** tab in Copilot Studio
3. Open the Teams conversation
4. Check the activity details:
   - **Correct**: Shows tool calls to `ccp___entity_extraction`, `normalize-ppml___normalize_ppml_term`, etc.
   - **Incorrect**: Shows "Search sources --> Knowledge" (means MCP connection failed)

---

## 13. How Users Access the Agent

### In Microsoft Teams

1. Open **Microsoft Teams**
2. Click **"Chat"** in the left sidebar
3. Click **"New chat"** or search for the agent name
4. Type: `IMO Health Diagnosis Specificity Agent`
5. Select it from the results
6. Start chatting with your clinical note

### In Microsoft 365 Copilot

1. Open **Microsoft 365 Copilot** (copilot.microsoft.com or via any M365 app)
2. Find the agent in the **Agent Store**
3. Click to start a conversation
4. Paste your clinical note

### On Demo Website

1. Open the demo website URL shared by admin
2. Type your clinical query in the chat box
3. Agent responds with normalized terms and specific codes

---

## 14. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Entity extraction returns no results | `ccp___entity_extraction` not authenticated | Check Tools --> mcp-gateway --> Connection status |
| "No usable lexical code returned" | MCP Gateway connection not authenticated | Re-authenticate mcp-gateway connection |
| Agent shows "Search sources --> Knowledge" | MCP tools unreachable, agent falls back | Verify mcp-gateway connection is green |
| Agent works in test but not Teams | Connection tied to maker session | Reconfigure with service credentials |
| Refinements not returned | Wrong code used in get_lexical | Ensure prompt specifies `default_lexical_code` |
| Slow response times | 5-6 sequential MCP tool calls | Expected behavior |
| Agent not appearing in Teams | Not yet approved | Wait 10-15 min after publishing, refresh Teams |

---

## 15. Publishing Checklist

### Before Publishing

- [ ] Agent tested end-to-end in test pane
- [ ] MCP Gateway connection shows green status
- [ ] All 5 required MCP tools enabled
- [ ] MCP connection configured with service-level authentication
- [ ] Instructions finalized and within character limit (8000 chars)
- [ ] Authentication set to "Authenticate with Microsoft"
- [ ] Agent name and description configured
- [ ] Greeting message set

### For Teams Deployment

- [ ] Teams channel enabled
- [ ] Availability set (teammates / organization)
- [ ] Published latest version
- [ ] Submitted for admin approval (if org-wide)
- [ ] Verified in Teams after approval

### For Marketplace

- [ ] Multi-tenant support enabled
- [ ] Partner Center account set up
- [ ] Icons and screenshots prepared
- [ ] Privacy policy and terms of use URLs ready
- [ ] Submission package complete
- [ ] Submitted for Microsoft certification

---

## Quick Reference

| Step | Action | Where |
|---|---|---|
| 1 | Create agent | Copilot Studio --> + Agent --> New agent |
| 2 | Add MCP server | Tools --> + Add action --> MCP |
| 3 | Configure OAuth | MCP server details --> Authentication |
| 4 | Enable tools | Tools --> mcp-gateway --> toggle tools |
| 5 | Set instructions | Overview --> Instructions --> Edit |
| 6 | Choose model | Settings --> Model |
| 7 | Test | Test panel (bottom-right) |
| 8 | Publish | Publish button (top-right) |
| 9 | Add channel | Channels --> Select channel --> Enable |

---

## Version History

| Date | Version | Change |
|---|---|---|
| 2026-05-29 | 1.0 | Initial publishing guide |
| 2026-06-01 | 1.1 | Added ccp___entity_extraction tool |
| 2026-06-25 | 2.0 | Combined build + publish into complete guide |
