# IMO Health MCP Server for Claude Code

Connect Claude Code to IMO Health's clinical intelligence MCP server — giving your AI assistant direct access to terminology normalization, clinical search, and knowledge graph capabilities through natural language.

## What is the IMO Health MCP Server?

The [IMO Health MCP server](https://developer.imohealth.com/mcp-server) exposes clinical terminology tools through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io), a standard interface that lets AI assistants call external tools. It connects your AI workflows to IMO's clinically validated terminology database — the same intelligence used across health systems nationwide to standardize problems, procedures, and codes.

When connected to Claude Code, you can ask questions like:

- "Normalize 'heart attack' to standard clinical terminology"
- "What's the most specific ICD-10 code for a patient with type 2 diabetes with diabetic nephropathy?"
- "Map SNOMED code 22298006 to ICD-10"

Claude will call the appropriate MCP tools behind the scenes, returning clinically precise results.

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

1. Go to [developer.imohealth.com](https://developer.imohealth.com)
2. Click **Log in** (top right) → **Create Account**
3. Complete the registration form and activate via email
4. Navigate to **My Credentials** (`/user/apps`)
5. Click **+ New Trial**, name your app, select the APIs you want access to
6. Click **Create Trial App**
7. Click the **View** icon on your app row to reveal:
   - **Consumer Key** → this is your `IMO_CLIENT_ID`
   - **Consumer Secret** → this is your `MCP_CLIENT_SECRET`

---

## Setup

### Step 1: Clone this repo

```bash
git clone https://github.com/imohealth/imo-mcp-guide.git
cd imo-mcp-guide
```

### Step 2: Export your credentials

Add your credentials to your shell profile so they persist across sessions:

```bash
echo 'export IMO_CLIENT_ID="<your_consumer_key>"' >> ~/.zshrc
echo 'export MCP_CLIENT_SECRET="<your_consumer_secret>"' >> ~/.zshrc
source ~/.zshrc
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

Once connected, Claude Code has access to **17 tools** across the following capability areas:

### Core Search

| Tool | Description |
|------|-------------|
| `mcp__imo-health__core-search___search_medical_term` | Searches for clinical concepts by free-text query across all domains |
| `mcp__imo-health__core-search___get_term_detail` | Retrieves detailed information for a specific clinical term |
| `mcp__imo-health__core-search___lookup_term_by_code` | Looks up a clinical term by a specific code (ICD, SNOMED, CPT, etc.) |

### GraphQL Modifier

| Tool | Description |
|------|-------------|
| `mcp__imo-health__graphql-modifier___get_allowed_refinements` | Gets allowed refinements for a clinical concept |
| `mcp__imo-health__graphql-modifier___get_cross_domain` | Retrieves cross-domain mappings for a concept |
| `mcp__imo-health__graphql-modifier___get_lexical` | Gets lexical variants and related terms |
| `mcp__imo-health__graphql-modifier___get_mappings` | Maps a concept across coding systems (ICD-10, SNOMED CT, CPT, etc.) |
| `mcp__imo-health__graphql-modifier___get_narrower_hierarchy` | Navigates the narrower/child hierarchy of a clinical concept |
| `mcp__imo-health__graphql-modifier___get_narrower_sequential_refinements` | Gets narrower sequential refinement options |
| `mcp__imo-health__graphql-modifier___get_narrower_with_refinements` | Gets narrower concepts with available refinements |
| `mcp__imo-health__graphql-modifier___get_refinement_group` | Retrieves refinement group details for a concept |
| `mcp__imo-health__graphql-modifier___get_related_problems` | Gets related problems and associations for a clinical concept |

### CCP (Clinical Content Processing)

| Tool | Description |
|------|-------------|
| `mcp__imo-health__ccp___entity_extraction` | Extracts clinical entities from free-text clinical notes |

### Categorize

| Tool | Description |
|------|-------------|
| `mcp__imo-health__categorize___categorize_problems` | Categorizes clinical problems into standardized groups |

### Normalize (PPML)

| Tool | Description |
|------|-------------|
| `mcp__imo-health__normalize-ppml___normalize_ppml_term` | Normalizes a free-text term to IMO's standard clinical terminology with mapped codes |

### IDE Tools

| Tool | Description |
|------|-------------|
| `mcp__ide__executeCode` | Executes code within the IDE environment |
| `mcp__ide__getDiagnostics` | Gets diagnostic information from the IDE |

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
