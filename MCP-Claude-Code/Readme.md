# IMO Health MCP Server for Claude Code

Connect Claude Code to IMO Health's clinical intelligence MCP server — giving your AI assistant direct access to terminology normalization, clinical search, and knowledge graph capabilities through natural language.

## What is the IMO Health MCP Server?

The [IMO Health MCP server](https://developer.imohealth.com/mcp-server) exposes clinical terminology tools through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io), a standard interface that lets AI assistants call external tools. It connects your AI workflows to IMO's clinically validated terminology database — the same intelligence used across health systems nationwide to standardize problems, procedures, and codes.

When connected to Claude Code, you can ask questions like:

- "Normalize 'heart attack' to standard clinical terminology"
- "What's the most specific ICD-10 code for a patient with type 2 diabetes with diabetic nephropathy?"
- "Map SNOMED code 22298006 to ICD-10"

Claude will call the appropriate MCP tools behind the scenes, returning clinically precise results.

## Features

- **36 clinical terminology tools** — Core Search, Normalization, Hierarchy Traversal, Cross-Mapping, Entity Extraction, Categorization, Concept Guidance, GuidelineCentral, Knowledge Graph Explorer, and Precision Literature Review.
- **Natural language interface** — ask questions in plain English; Claude calls the right MCP tools behind the scenes.
- **Multi-system code mapping** — translate between ICD-10-CM, SNOMED CT, CPT, RxNorm, NDC, and IMO vocabularies in one step.
- **Clinical entity extraction** — pull structured diagnoses, procedures, and medications from free-text notes.
- **Hierarchy navigation** — explore parent/child concept relationships to find more specific or broader terms.
- **Clinical practice guidelines** — search and retrieve GuidelineCentral documents with presigned PDF links and semantic search.
- **Knowledge Graph exploration** — inspect schema, run SPARQL queries, and traverse cross-domain clinical relationships.
- **Precision Literature Review** — manage PLR projects, screen citations, retrieve PRISMA charts and extracted study data.
- **Diagnostic specificity agents** — automated pipelines that refine codes to the highest supported level of detail.
- **Plugin-based setup** — install via Claude Code marketplace with OAuth authentication and credential management built in.
- **Guided onboarding** — run `/imo-mcp-connect` for step-by-step authentication and connection verification.

---

## Why Connect to Claude Code?

Claude Code is an agentic coding assistant that can chain tool calls together to solve complex problems. By connecting the IMO Health MCP server, you enable Claude to:

1. **Normalize free-text clinical terms** into standardized codes without manual lookup
2. **Search across coding systems** (ICD-10, SNOMED CT, CPT) with natural language
3. **Traverse clinical hierarchies** to find more specific or more general concepts
4. **Cross-map between systems** in a single conversational request
5. **Build clinical agents** that combine multiple tool calls into automated workflows

This turns Claude Code into a clinical terminology workstation — useful for developers building health IT systems, clinical informaticists mapping data, and anyone who needs to work with medical codes programmatically.

## This Repository

This repo is a **Claude Code plugin** that registers the IMO Health MCP server automatically. Instead of manually configuring server URLs and auth headers, you clone this repo, install the plugin, and authenticate through your browser. The plugin handles:

- MCP server registration (URL, OAuth scopes)
- Credential management via environment variables
- A setup skill (`/imo-mcp-connect`) that walks you through authentication

---

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed (`claude --version` to confirm)
- A registered [IMO Health developer account](https://developer.imohealth.com)
- API credentials (Consumer Key & Consumer Secret) from the developer portal

### Getting Your Credentials

This guide assumes that one already has API credentials for the IMO Health MCP server with a client id and secret. If you do not have credentials, please contact the IMO Health API team at support.imohealth.com in order to receive the appropriate credentials to walk through this repository. 

## Setup

### Step 1: Clone this repo

```bash
git clone https://github.com/imohealth/solution-accelerators.git
cd solution-accelerators/MCP-Claude-Code
```

### Step 2: Export your credentials

Add your credentials to your shell profile so they persist across sessions:

```bash
echo 'export IMO_CLIENT_ID="<your_consumer_key>"' >> ~/.zshrc
echo 'export MCP_CLIENT_SECRET="<your_consumer_secret>"' >> ~/.zshrc
source ~/.zshrc
```
OR

```bash
echo 'export IMO_CLIENT_ID="<your_consumer_key>"' >> ~/.bashrc
echo 'export MCP_CLIENT_SECRET="<your_consumer_secret>"' >> ~/.bashrc
source ~/.bashrc
```

> **Security note:** Never commit credentials to version control. These environment variables are referenced by the plugin at runtime.

### Step 3: Add the marketplace and install the plugin

Claude Code uses a marketplace/plugin system to manage MCP server integrations. This repo is structured as a marketplace containing one plugin (`imo-health`):

```bash
# Register this repo as a local marketplace
claude plugin marketplace add ./

# Install the IMO Health plugin from it
claude plugin install imo-health@imo-health-marketplace
```

**What this does:**
- `marketplace add` tells Claude Code that this directory contains installable plugins
- `plugin install` registers the MCP server configuration and the `/imo-mcp-connect` setup skill

### Step 4: Authenticate

Start a new Claude Code session:

```bash
claude
```

On first connection, Claude Code will trigger the OAuth flow:

1. Your browser opens to the IMO Health authorization page
2. Log in with your IMO Health developer credentials
3. Grant access to the requested scopes (`normalize`, `search`, etc.)
4. The browser redirects back and the token is stored automatically

> If the OAuth flow doesn't trigger automatically, run `/imo-mcp-connect` in Claude Code — the skill will check your credentials and guide you through authentication.

### Step 5: Verify

In your Claude Code session, run:

```
/mcp
```

You should see `imo-health` listed with a green checkmark and its tools available.

---

## Available Tools

Once connected, Claude Code has access to **36 tools** across the following capability areas:

### CCP (Clinical Content Processing)

| Tool | Description |
|------|-------------|
| `mcp__imo-health__ccp___entity_extraction` | Extract clinical entities (problems, medications, labs, allergens) from free text using IMO CCP NLP with code mappings to ICD-10-CM, SNOMED, UMLS, and IMO terminologies |

### Core Search

| Tool | Description |
|------|-------------|
| `mcp__imo-health__core-search___search_medical_term` | Search for medical terms using IMO Core Search API (ProblemIT Professional) with ranked results including IMO lexical codes, ICD-10-CM, SNOMED CT, and HCC risk categories |
| `mcp__imo-health__core-search___get_term_detail` | Get detailed supplemental information for IMO lexical codes including mapped codes, HCC risk categories, and clinical attributes |
| `mcp__imo-health__core-search___lookup_term_by_code` | Look up medical terms by IMO lexical codes with term title, ICD-10-CM/SNOMED mappings, and clinical attributes |

### Normalize (PPML)

| Tool | Description |
|------|-------------|
| `mcp__imo-health__normalize-ppml___normalize_ppml_term` | Normalize medical terms using the IMO Precision Normalize API across Problem, Procedure, Medication, and Lab domains |

### Categorize

| Tool | Description |
|------|-------------|
| `mcp__imo-health__categorize___categorize_problems` | Organize clinical problems into intuitive disease categories using IMO clinical intelligence |

### Knowledge Graph (GraphQL Modifier)

| Tool | Description |
|------|-------------|
| `mcp__imo-health__graphql-modifier___get_allowed_refinements` | Look up allowed refinements (modifiers) for an IMO Problem lexical — laterality, chronicity, location, etc. |
| `mcp__imo-health__graphql-modifier___get_cross_domain` | Discover cross-domain clinical relationships — diagnostics, treatments, etiology, temporally-related concepts |
| `mcp__imo-health__graphql-modifier___get_lexical` | Look up an IMO lexical with title, broader concepts, applied refinements, and allowed refinements |
| `mcp__imo-health__graphql-modifier___get_mappings` | Retrieve external code mappings (ICD-10-CM, SNOMED CT, CPT, RxNorm, NDC, etc.) with relationship types |
| `mcp__imo-health__graphql-modifier___get_narrower_hierarchy` | Explore two levels up and down the problem hierarchy to identify related terms at different specificity levels |
| `mcp__imo-health__graphql-modifier___get_narrower_sequential_refinements` | Apply refinements as nested traversal to find progressively more specific IMO lexicals in a single query |
| `mcp__imo-health__graphql-modifier___get_narrower_with_refinements` | Get narrower IMO lexicals filtered by specific refinement criteria (e.g., laterality:right) |
| `mcp__imo-health__graphql-modifier___get_refinement_group` | Look up all refinement options within a category (e.g., all laterality options: right, left, bilateral) |
| `mcp__imo-health__graphql-modifier___get_related_problems` | Find clinical problems related to a procedure or medication (reverse lookup) |
| `mcp__imo-health__graphql-modifier___get_broader_refinements` | Find immediate parents of a Problem lexical in its refinement family (each parent drops one refinement) |
| `mcp__imo-health__graphql-modifier___get_medication_ingredients` | Find a medication product's active ingredients or find products containing a given ingredient |
| `mcp__imo-health__graphql-modifier___get_narrower_by_medications` | Find children of a Problem lexical that have treatment relationships with supplied medications |
| `mcp__imo-health__graphql-modifier___get_narrower_by_procedures` | Find children of a Problem lexical that have evaluation/treatment relationships with supplied procedures |

### Concept and Editorial Guidance

| Tool | Description |
|------|-------------|
| `mcp__imo-health__concept-guideline___get_concept_candidates` | Find ranked IMO Clinical Interface Terminology candidates for a Problem-domain term with word-overlap scores |
| `mcp__imo-health__concept-guideline___search_editorial_kb` | Find relevant excerpts from IMO's editorial knowledge base on naming, formatting, and migration policies |

### GuidelineCentral

| Tool | Description |
|------|-------------|
| `mcp__imo-health__guidelinecentral-search___list_documents` | List available GuidelineCentral documents with IDs, titles, source organizations, and page counts |
| `mcp__imo-health__guidelinecentral-search___search_guidelines` | Search clinical practice guidelines by meaning with ranked excerpts, relevance scores, and presigned PDF links |
| `mcp__imo-health__guidelinecentral-search___search_within_document` | Search within one GuidelineCentral document by meaning |
| `mcp__imo-health__guidelinecentral-search___search_by_imo_codes` | Find guideline excerpts indexed with supplied IMO lexical codes |
| `mcp__imo-health__guidelinecentral-search___get_guideline` | Retrieve a guideline's metadata, presigned PDF URL, and full text grouped by page |

### Knowledge Graph Explorer

| Tool | Description |
|------|-------------|
| `mcp__imo-health__knowledge-graph-explorer___explore_schema` | Inspect the Knowledge Graph's named graphs, classes, predicates, or sample triples for use in SPARQL queries |
| `mcp__imo-health__knowledge-graph-explorer___run_sparql` | Run a read-only SPARQL query against the Knowledge Graph (SELECT, ASK, CONSTRUCT, or DESCRIBE) |

### Precision Literature Review (PLR)

| Tool | Description |
|------|-------------|
| `mcp__imo-health__plr___list_projects` | List owned and shared PLR projects with ID, name, disease, type, workflow step, and role |
| `mcp__imo-health__plr___get_project` | Retrieve one PLR project's details including status, workflow step, and project link |
| `mcp__imo-health__plr___get_study_protocols` | Retrieve literature search details, inclusion/exclusion criteria, and extraction fields for projects |
| `mcp__imo-health__plr___get_screening_counts` | Retrieve AI and human screening counts, agreement/disagreement counts for projects |
| `mcp__imo-health__plr___search_citations` | Find citations within a project with publication metadata, AI/human decisions, and full-text availability |
| `mcp__imo-health__plr___get_citation_ai_result` | Retrieve the AI's predicted study types, screening explanation, and matched exclusion criteria |
| `mcp__imo-health__plr___get_prisma` | Retrieve PRISMA flow chart counts for identification, screening, eligibility, and inclusion |
| `mcp__imo-health__plr___get_data_summary` | Retrieve extracted study data with columns, rows, sorting, and link to the full table |

---

## Building a Diagnostic Specificity Agent

One powerful use case is building an agent that takes a clinical note and finds the **highest degree of diagnostic specificity** — the most precise, billable code that matches the clinical documentation.

### Why Specificity Matters

Health systems lose revenue and create compliance risk when they code to unspecified or less-specific diagnoses. A note that says "patient has diabetes with kidney involvement" should map to a highly specific code like **E11.21** (Type 2 diabetes mellitus with diabetic nephropathy), not the generic **E11.9** (Type 2 diabetes mellitus without complications).

The IMO MCP tools let you build an agent that automates this specificity refinement.

### How It Works

The agent follows a three-step pipeline using the MCP tools:

```
Clinical Note → Normalize → Search Hierarchy → Select Most Specific Code
```

**Step 1: Normalize the clinical term**
Extract the relevant diagnosis from the note and normalize it to a standard concept using `normalize_problem`. This gives you the IMO ID and initial code mappings.

**Step 2: Explore the hierarchy for greater specificity**
Use `get_hierarchy` on the normalized concept to see its child concepts — more specific variants that might better match the clinical documentation. Then use `get_relationships` to see associated qualifiers (laterality, severity, type).

**Step 3: Cross-map to the target code system**
Once you've identified the most specific concept that matches the documentation, use `cross_map` to get the corresponding ICD-10-CM, SNOMED CT, or CPT code.

### Example Walkthrough

Given this clinical note:

> "58-year-old male presents with chest pain. ECG shows ST-elevation. Troponin elevated. Assessment: acute myocardial infarction of the anterior wall."

Here's how the agent would process it:

---

**1. Normalize the diagnosis**

The agent calls `normalize_problem` with the term "acute myocardial infarction of the anterior wall":

```
→ normalize_problem("acute myocardial infarction of the anterior wall")

Returns:
  IMO ID: "Acute ST elevation myocardial infarction of anterior wall"
  ICD-10-CM: I21.09
  SNOMED CT: 54329005
```

The normalization step already identifies a specific concept, but the agent checks if there's something even more precise.

---

**2. Explore the hierarchy**

The agent calls `get_hierarchy` on the returned concept to see child (more specific) concepts:

```
→ get_hierarchy("Acute ST elevation myocardial infarction of anterior wall")

Returns hierarchy:
  Parent: Acute myocardial infarction (I21)
  Current: Acute ST elevation MI of anterior wall (I21.09)
  Children:
    - Acute ST elevation MI of left anterior descending artery (I21.02)
    - Acute ST elevation MI of left main coronary artery (I21.01)
    - Acute ST elevation MI of other anterior wall (I21.09)
```

The agent then calls `get_relationships` to check for associated qualifiers:

```
→ get_relationships("Acute ST elevation myocardial infarction of anterior wall")

Returns:
  - Associated morphology: Infarct
  - Finding site: Anterior wall of heart
  - Associated with: ST segment elevation
```

---

**3. Select the most specific match**

Based on the clinical note (which says "anterior wall" but doesn't specify which artery), the agent determines that **I21.09** (ST elevation MI involving other anterior wall) is the most specific code supported by the documentation. It wouldn't be appropriate to code to I21.02 (LAD artery) because the note doesn't document which specific artery was involved.

---

**4. Cross-map for additional systems**

If you also need SNOMED CT or CPT codes:

```
→ cross_map("I21.09", from="ICD-10-CM", to="SNOMED-CT")

Returns:
  SNOMED CT: 401303003 - Acute ST segment elevation myocardial infarction of anterior wall
```

### Running This as a Prompt

You don't need to build custom code — just prompt Claude Code directly:

```
Given this clinical note, find the most specific ICD-10-CM code supported
by the documentation. Use the IMO tools to normalize the diagnosis, explore
the hierarchy for more specific options, and explain why you chose the final
code.

Note: "58-year-old male presents with chest pain. ECG shows ST-elevation.
Troponin elevated. Assessment: acute myocardial infarction of the anterior wall."
```

Claude Code will chain `normalize_problem` → `get_hierarchy` → `get_relationships` → `cross_map` automatically to arrive at the most specific defensible code.

### Extending the Agent

You can expand this pattern for more complex scenarios:

- **Batch processing**: Feed multiple diagnoses from a note through `batch_normalize`, then refine each one
- **Multi-system mapping**: Use `cross_map` to produce ICD-10, SNOMED, and CPT codes simultaneously
- **Specificity validation**: Use `get_hierarchy` to verify that a code isn't "unspecified" when more specific options exist
- **Autocomplete workflows**: Use `get_suggestions` to surface candidate diagnoses as a clinician types

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Needs authentication" in `/mcp` | Start a new Claude Code session to re-trigger the OAuth browser flow |
| OAuth browser doesn't open | Restart Claude Code; check that your default browser opens from terminal |
| 401 Unauthorized | Token expired — restart Claude Code to trigger auto-refresh |
| Redirect URI mismatch | After first connection, copy the callback URL from Claude Code and add it to Auth0 Allowed Callback URLs in the IMO developer portal |
| Plugin not found during install | Ensure you ran `claude plugin marketplace add ./` first |
| Environment variables not found | Run `source ~/.zshrc` and confirm with `echo $IMO_CLIENT_ID` |
| 429 Too Many Requests | Rate limit hit — wait and retry. Check the `Retry-After` header |

---

## Uninstalling

```bash
claude plugin uninstall imo-health
claude plugin marketplace remove imo-health-marketplace
```

---

## Resources

- [IMO Health Developer Portal](https://developer.imohealth.com)
- [IMO MCP Server Documentation](https://developer.imohealth.com/mcp-server)
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Model Context Protocol Specification](https://modelcontextprotocol.io)
