# IMO Health Clinical Intelligence Plugin

Clinical terminology normalization, knowledge graph navigation, and code-system cross-mapping powered by IMO Health MCP.

## What This Plugin Does

Connect to IMO Health's MCP server to access 36 clinical terminology tools:

- **Normalize** medical terms across Problem, Procedure, Medication, and Lab domains
- **Search** clinical concepts by free text or code
- **Map** between ICD-10-CM, SNOMED CT, CPT, RxNorm, HCPCS, LOINC, and 10+ code systems
- **Navigate** the IMO Knowledge Graph — hierarchies, refinements, cross-domain relationships
- **Extract** clinical entities from free-text notes (discharge summaries, progress notes)
- **Categorize** problem lists by disease category
- **Drill down** to the most specific ICD-10 code using diagnosis specificity refinements
- **Search clinical guidelines** from GuidelineCentral with semantic search and presigned PDF links
- **Explore the Knowledge Graph** schema and run SPARQL queries directly
- **Manage literature reviews** via Precision Literature Review — projects, screening, citations, PRISMA charts
- **Concept guidance** — find ranked IMO candidates and search editorial naming/formatting policies

## Prerequisites

- **Node.js** (v18+) — https://nodejs.org
- **OpenAI Codex CLI** — install with `npm install -g @openai/codex`
- **Python** (for setup script)
- **Git**
- **IMO Health credentials** (Client ID and Client Secret) — contact your IMO team

## Quick Start (Automated)

```bash
# 1. Clone the repo
git clone <repo-url>
cd IMO-Codex-Using-Extension

# 2. Run setup
bash setup.sh
```

The setup script will:
1. Register the local marketplace
2. Install the plugin
3. Prompt for your IMO credentials (Client ID and Client Secret)
4. Add the MCP server to your Codex config

After setup:
```bash
# 3. Launch Codex
codex

# 4. Authenticate the MCP server
/mcp login IMO-HEALTH-MCP-SERVER

# 5. Verify connection
/mcp
# Should show: IMO-HEALTH-MCP-SERVER: connected (36 tools)

# 6. Test it
Normalize chest pain
```

## Manual Setup

If you prefer to set up manually instead of using `setup.sh`:

### Step 1 — Register the marketplace

```bash
codex plugin marketplace add /path/to/IMO-Codex-Using-Extension
```

### Step 2 — Install the plugin

```bash
codex plugin add imo-health-clinical-intelligence@imo-health-codex-marketplace
```

### Step 3 — Set credentials

**Bash (Mac/Linux/Git Bash):**
```bash
export IMO_CLIENT_ID="<your-client-id>"
export MCP_CLIENT_SECRET="<your-client-secret>"
```

To make permanent:
```bash
echo 'export IMO_CLIENT_ID="<your-client-id>"' >> ~/.bashrc
echo 'export MCP_CLIENT_SECRET="<your-client-secret>"' >> ~/.bashrc
source ~/.bashrc
```

**PowerShell (Windows):**
```powershell
$env:IMO_CLIENT_ID="<your-client-id>"
$env:MCP_CLIENT_SECRET="<your-client-secret>"
```

### Step 4 — Add MCP server to Codex config

Add this block to `~/.codex/config.toml`:

```toml
[mcp_servers.IMO-HEALTH-MCP-SERVER]
enabled = true
url = "https://api.imohealth.com/mcp"
```

**PowerShell (Windows):**
```powershell
Add-Content ~/.codex/config.toml "`n[mcp_servers.IMO-HEALTH-MCP-SERVER]`nenabled = true`nurl = `"https://api.imohealth.com/mcp`""
```

### Step 5 — Launch and authenticate

```bash
codex
```

Inside Codex:
```
/mcp login IMO-HEALTH-MCP-SERVER
```

### Step 6 — Verify

```
/mcp
```

You should see `IMO-HEALTH-MCP-SERVER: connected (36 tools)`.

### Step 7 — Verify in Codex Settings

Open Codex settings to confirm the plugin and marketplace are visible:

1. Open **Codex Settings** (gear icon or `/settings`)
2. Go to the **Plugins** section
3. You should see:
   - **Marketplace:** `imo-health-codex-marketplace` listed as a local source
   - **Plugin:** `IMO Health Clinical Intelligence` installed and enabled

## ChatGPT Web Plugin

This plugin can also be used on ChatGPT web:

1. Go to chatgpt.com/plugins
2. Click **+** then **Upload plugin archive**
3. Upload the plugin ZIP (containing `plugin.json`, `mcp.json`, `skills/`)
4. Connect the MCP server through the portal
5. Test in a new chat

## Available Skills

| Skill | Description |
|-------|-------------|
| **imo-clinical-tools** | Master guide to all 36 MCP tools — decision tree, workflows, formatting rules |
| **setup** | Installation and authentication walkthrough |

---

## MCP Tools (36 Tools)

The agent uses the following tools from the IMO Health MCP server:

---

### CCP (Clinical Content Processing)

#### 1. `mcp__imo-health__ccp___entity_extraction`

**Description:** Extract clinical entities (problems, medications, labs, allergens) from free text using IMO CCP NLP. Analyzes clinical text to identify medical entities with semantic information and code mappings to ICD-10-CM, SNOMED, UMLS, and IMO terminologies.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `text` | string | Yes | Clinical text to extract entities from, such as a discharge summary or progress note. |
| `version` | string | No | API version. Default: 3.0. |

---

### Core Search

#### 2. `mcp__imo-health__core-search___search_medical_term`

**Description:** Search for medical terms using the IMO Core Search API (ProblemIT Professional). Returns ranked search results with IMO lexical codes, titles, and mapped codes (ICD-10-CM, SNOMED CT, HCC risk categories). Use the returned IMO lexical codes with `get_term_detail` for supplemental information, or with the Knowledge Graph `get_lexical` tool for modifier/refinement data.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `search_term` | string | Yes | The medical term to search for, such as 'chest pain' or 'diabetes'. |
| `number_of_results` | integer | No | Maximum number of search results to return. Default: 10. |

---

#### 3. `mcp__imo-health__core-search___get_term_detail`

**Description:** Get detailed supplemental information for IMO lexical codes via the Core Search API. Returns the full detail payload for each code, including mapped codes (ICD-10-CM, SNOMED CT), HCC risk categories, and clinical attributes. Use IMO lexical codes obtained from `search_medical_term` or `normalize_medical_term` results.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `codes` | string | Yes | Comma-separated IMO lexical codes to get details |

---

#### 4. `mcp__imo-health__core-search___lookup_term_by_code`

**Description:** Look up medical terms by their IMO lexical codes using the Core Search API. Returns the search payload for each known IMO lexical code, including the term title, ICD-10-CM/SNOMED mappings, and clinical attributes. Use this when you already have IMO lexical codes (e.g., from `normalize_medical_term`) and need the Core Search terminology data for those codes.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `codes` | string | Yes | Comma-separated IMO lexical codes to look up |

---

### Normalize (PPML)

#### 5. `mcp__imo-health__normalize-ppml___normalize_ppml_term`

**Description:** Normalize medical terms using the IMO Precision Normalize API across Problem, Procedure, Medication, and Lab domains. Send one or more medical terms and receive raw normalization results from the API. For Medication domain, returns 20 results per term. For Problem, Procedure, and Lab domains, returns 1 result per term.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `terms` | array of strings | Yes | List of medical terms to normalize, such as ['diabetes', 'chest pain', 'amoxicillin', 'CBC']. |
| `domain` | string | Yes | The domain of the medical terms. Must be one of: 'Problem', 'Procedure', 'Medication', or 'Lab'. |

---

### Categorize

#### 6. `mcp__imo-health__categorize___categorize_problems`

**Description:** Organize a list of clinical problems into intuitive disease categories. Groups related conditions together using IMO clinical intelligence to declutter problem lists. Useful for patient chart review and clinical summaries.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `problems` | array of objects | Yes | List of problems to categorize. Each problem is an object with keys such as id, title, lexical_code, icd10, and snomed. At least one of title, icd10, or snomed is required. |
| `priority_specialty` | string or null | No | Optional provider specialty code to prioritize in category ordering. |

---

### Knowledge Graph (GraphQL Modifier)

#### 7. `mcp__imo-health__graphql-modifier___get_allowed_refinements`

**Description:** Look up allowed refinements (also known as modifiers) for an IMO Problem lexical in the Knowledge Graph. Returns the refinement group(s) and refinement option(s) that can be applied to make the IMO lexical more specific (e.g., laterality, chronicity, location). Each allowed refinement includes its group code and title for categorization.

**Important:** Use the lexical_code value from normalize_medical_term results as the code parameter (NOT the imo_code). Allowed refinements are only available for the 'problem' domain.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `imo_lexical_code` | string | Yes | The lexical_code from normalize_medical_term results, such as 'imo_code' for knee pain. |
| `domain` | string | No | The lexical domain. Default: 'problem'. |

---

#### 8. `mcp__imo-health__graphql-modifier___get_cross_domain`

**Description:** Discover cross-domain clinical relationships for an IMO Problem lexical in the Knowledge Graph. Returns clinical relationships linked to the problem across other domains: associated diagnostics/findings/procedures/lab procedures, treatments (primary/supportive/preventative/contraindicated medications), causative agents and due-to causes (etiology), temporally-related concepts (during/after/before), realizations, finding methods, routine lab procedures, and interpreted procedures.

**Important:** Use the lexical_code value from normalize_medical_term results as the code parameter (NOT the imo_code).

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `imo_lexical_code` | string | Yes | The lexical_code from normalize_medical_term results, such as 'imo_code' for carcinoma of right breast or 'imo_code' for Crohn's disease. |

---

#### 9. `mcp__imo-health__graphql-modifier___get_lexical`

**Description:** Look up an IMO lexical in the IMO Health Knowledge Graph by its lexical code. Returns the title, broader (parent) concepts, applied refinements (refinements already reflected in the lexical), and allowed refinements grouped by category. Use the allowed refinements to understand what options can increase diagnostic specificity.

**Important:** Use the lexical_code value from normalize_medical_term results as the code parameter (NOT the imo_code). Applied refinements and allowed refinements are only available for the 'problem' domain.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `imo_lexical_code` | string | Yes | The lexical_code from normalize_medical_term results, such as 'imo_code' |
| `domain` | string | No | The lexical domain. Default: 'problem'. |

---

#### 10. `mcp__imo-health__graphql-modifier___get_mappings`

**Description:** Retrieve external code mappings for an IMO lexical from the Knowledge Graph. Returns equivalent codes in industry standard coding systems. Problem: ICD-10-CM, ICD-10-CA, ICD-9-CM, SNOMED CT, DSM-5, ICD-O, MONDO. Procedure: CPT, HCPCS, ICD-10-PCS, LOINC, SNOMED CT. Medication: RxNorm, NDC, CVX, SNOMED CT. Each mapping includes the code, title, code system, and relationship type (exactMatch, closeMatch, broadMatch, narrowMatch, relatedMatch).

**Important:** Use the lexical_code value from normalize_medical_term results as the code parameter (NOT the imo_code).

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `imo_lexical_code` | string | Yes | The lexical_code from normalize_medical_term results, such as 'imo_code' for knee pain. |
| `domain` | string | No | The lexical domain: 'problem' (default), 'procedure', or 'medication'. |
| `code_systems` | array of strings or null | No | Optional list of code systems to filter by, such as icd10cm, snomedInternational, rxnorm, or cpt. |
| `include_hcc` | boolean | No | Problem domain only. If true, include HCC data on ICD-10-CM mappings. Default: false. |

---

#### 11. `mcp__imo-health__graphql-modifier___get_narrower_hierarchy`

**Description:** Explore the hierarchy of an IMO lexical in the Knowledge Graph — both up and down. Returns two levels of broader (parent, grandparent) and two levels of narrower (children, grandchildren) IMO lexicals from the problem hierarchy. Use this to navigate the hierarchy and identify related terms at different specificity levels.

**Important:** Use the lexical_code value from normalize_medical_term results as the code parameter (NOT the imo_code). The problem hierarchy is only available for the 'problem' domain.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `imo_lexical_code` | string | Yes | The lexical_code from normalize_medical_term results, such as 'imo_code' for knee pain. |
| `domain` | string | No | The lexical domain. Default: 'problem'. |

---

#### 12. `mcp__imo-health__graphql-modifier___get_narrower_sequential_refinements`

**Description:** Apply refinements as nested GraphQL traversal to find progressively more specific IMO lexicals. Builds a single nested GraphQL query where each refinement level creates a deeper narrower() call. The depth of nesting is determined dynamically by the length of refinement sequence. Ideal for agents that need to drill down through multiple refinement levels in a single query.

**Important:** Use the lexical_code value from normalize_medical_term results as the code parameter (NOT the imo_code).

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `imo_lexical_code` | string | Yes | The starting lexical_code from normalize_medical_term results, such as 'imo_code' |
| `refinement_sequence` | array of arrays of strings | Yes | Ordered sequence of refinement code lists to apply as nested filters. Example: 'imo_code' creates three levels of nesting. |
| `domain` | string | No | The lexical domain. Default: 'problem'. |
| `include_allowed_refinements` | boolean | No | If true, include allowedRefinements at every nesting level. Default: false. |
| `include_mappings` | boolean | No | If true, include code mappings such as ICD-10 and SNOMED at the deepest level. Default: false. |

---

#### 13. `mcp__imo-health__graphql-modifier___get_narrower_with_refinements`

**Description:** Get narrower IMO lexicals filtered by specific refinement criteria. Returns only the narrower (more specific) IMO lexicals that match the given refinement codes. Use this after calling `get_allowed_refinements` to filter children by specific refinement options (e.g., find all knee pain variants with laterality:right).

**Important:** Use the lexical_code value from normalize_medical_term results as the code parameter (NOT the imo_code). Applied refinements are only available for the 'problem' domain.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `imo_lexical_code` | string | Yes | The lexical_code from normalize_medical_term results, such as 'imo_code' for knee pain. |
| `refinement_codes` | array of strings | Yes | List of refinement codes to filter narrower lexicals by, such as 'imo_code' for laterality:right. |
| `domain` | string | No | The lexical domain. Default: 'problem'. |

---

#### 14. `mcp__imo-health__graphql-modifier___get_refinement_group`

**Description:** Look up all refinements within a specific refinement group. Returns the group title and all available refinement options within the category. Use this to see all possible values for a refinement type (e.g., all laterality options: right, left, bilateral, unilateral, unspecified). Get the group notation from the group. Code field in get_allowed_refinements or get_lexical results.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `notation` | string | Yes | The refinement group notation/code, such as 'imo_code' for laterality. |

---

#### 15. `mcp__imo-health__graphql-modifier___get_related_problems`

**Description:** Find the clinical problems related to a procedure or medication (reverse lookup). Traverses the cross-domain graph in reverse. Procedure: returns historicalProblems, interpretedFindings, determinedProblems, causedProblems, realizedProblems. Medication: returns treatedProblems, contraindicatedProblems, preventedProblems, causedProblems.

**Important:** Use the lexical_code value from normalize_medical_term results as the code parameter (NOT the imo_code).

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `imo_lexical_code` | string | Yes | The lexical_code of a procedure or medication from normalize_medical_term results. |
| `domain` | string | No | The domain of the input code: 'procedure' or 'medication'. Default: 'procedure'. |

---

### Concept and Editorial Guidance

#### 16. `mcp__imo-health__concept-guideline___get_concept_candidates`

**Description:** Find ranked IMO Clinical Interface Terminology candidates for a Problem-domain term. Each candidate has an IMO concept ID, a name, and a word-overlap score from 0 to 1.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `term` | string | Yes | Free-text clinical term, 1–1,000 characters. |
| `source_type` | string | No | Vocabulary label. Accepted aliases are `ICD10`, `ICD-10-CM`, `SNOMED`, `SNOMEDCT`, `SNOMED-CT`, and `IMO`. |
| `top_n` | number | No | Maximum number of ranked candidates to return (1-50). |

---

#### 17. `mcp__imo-health__concept-guideline___search_editorial_kb`

**Description:** Find relevant excerpts from IMO's editorial knowledge base on naming, formatting, and migration policies. Each result includes the source, text, and relevance score.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | Free-text search query (1-1000 chars). |
| `top_n` | number | No | Maximum number of KB chunks to return (1-25). |

---

### Additional Knowledge Graph Tools

#### 18. `mcp__imo-health__graphql-modifier___get_broader_refinements`

**Description:** Find the immediate parents of a Problem lexical in its refinement family. Each parent drops one refinement.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `imo_lexical_code` | string | Yes | IMO `lexical_code` from normalization. Use a Problem lexical. |
| `offset` | number | No | Zero-based result offset. Returns up to 100 items per call. |

---

#### 19. `mcp__imo-health__graphql-modifier___get_medication_ingredients`

**Description:** Find a medication product's active ingredient lexicals or find products that contain a given ingredient.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `imo_lexical_code` | string | Yes | IMO `lexical_code` from normalization. Use a Medication lexical. |
| `direction` | string | No | `ingredients` finds active ingredients in a product. `containing` finds products that contain the supplied ingredient. |
| `offset` | number | No | Zero-based result offset. Returns up to 100 items per call. |

---

#### 20. `mcp__imo-health__graphql-modifier___get_narrower_by_medications`

**Description:** Find the immediate children of a Problem lexical that have a treatment or supportive-treatment relationship with every supplied medication.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `imo_lexical_code` | string | Yes | IMO `lexical_code` from normalization. Use a Problem lexical. |
| `medication_codes` | array of strings | Yes | One or more Medication lexical codes from normalization. Every supplied code must match. |
| `offset` | number | No | Zero-based result offset. Returns up to 100 items per call. |

---

#### 21. `mcp__imo-health__graphql-modifier___get_narrower_by_procedures`

**Description:** Find the immediate children of a Problem lexical that have an evaluation, treatment, prevention, or evaluation-lab relationship with every supplied procedure.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `imo_lexical_code` | string | Yes | IMO `lexical_code` from normalization. Use a Problem lexical. |
| `procedure_codes` | array of strings | Yes | One or more Procedure lexical codes from normalization. Every supplied code must match. |
| `offset` | number | No | Zero-based result offset. Returns up to 100 items per call. |

---

### GuidelineCentral

#### 22. `mcp__imo-health__guidelinecentral-search___list_documents`

**Description:** List available GuidelineCentral documents with document IDs, names, titles, source organizations, publication dates, and page counts.

**Parameters:**

No parameters required.

---

#### 23. `mcp__imo-health__guidelinecentral-search___search_guidelines`

**Description:** Search clinical practice guidelines by meaning. Results include ranked excerpts, relevance scores, source metadata, and presigned links to PDFs and page images.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | Natural language query to search clinical practice guidelines. |
| `top_k` | number | No | Number of results to return (1-50, default 10). |

---

#### 24. `mcp__imo-health__guidelinecentral-search___search_within_document`

**Description:** Search within one GuidelineCentral document by meaning. Results include the highest-ranked matching excerpts.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | Yes | Guideline document UUID from a guideline search or the document catalog. |
| `query` | string | Yes | Natural language query to search within the document. |
| `top_k` | number | No | Number of results to return (1-50, default 10). |

---

#### 25. `mcp__imo-health__guidelinecentral-search___search_by_imo_codes`

**Description:** Find guideline excerpts indexed with the supplied IMO lexical codes. Results include the matched entities and code details.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `imo_lexical_codes` | array of strings | Yes | List of IMO lexical codes to search for (e.g., ['41884', '54321']). |
| `limit` | number | No | Maximum results to return (1-200, default 50). |

---

#### 26. `mcp__imo-health__guidelinecentral-search___get_guideline`

**Description:** Retrieve a guideline's metadata, presigned PDF URL, and full text grouped by page with page-image URLs.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | Yes | Guideline document UUID from a guideline search or the document catalog. |

---

### Knowledge Graph Explorer

#### 27. `mcp__imo-health__knowledge-graph-explorer___explore_schema`

**Description:** Inspect the Knowledge Graph's named graphs, classes with counts, predicates with counts, or up to 25 sample triples for a class. Use the returned identifiers in SPARQL queries.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `section` | string enum (`named_graphs`, `classes`, `predicates`, `sample_class`) | Yes | Schema section to retrieve. |
| `class_iri` | string or null | No | Required when section='sample_class'. Full IRI of the class to sample instances of. |
| `graph` | string or null | No | Optional named-graph IRI to scope the query to. |

---

#### 28. `mcp__imo-health__knowledge-graph-explorer___run_sparql`

**Description:** Run a read-only SPARQL query and receive the query result plus flattened rows for `SELECT`. Queries must be under 10,000 characters and finish within 50 seconds.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | A read-only SPARQL query (SELECT, ASK, CONSTRUCT, or DESCRIBE). |
| `limit` | number or null | No | Row limit to inject into `SELECT` queries without a `LIMIT`. Defaults to 100, capped at 1,000. |

---

### Precision Literature Review

#### 29. `mcp__imo-health__plr___list_projects`

**Description:** List owned and shared PLR projects, most recently updated first. Results include project ID, name, disease, description, type, workflow step, last updated date, user role, and project link.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name_filter` | string or null | No | Literal text that must appear in the project name. Omit for topic questions. |

---

#### 30. `mcp__imo-health__plr___get_project`

**Description:** Retrieve one PLR project's name, description, disease, type, status, current workflow step, last updated date, and project link.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `project_id` | string | Yes | Project ID from `list_projects`. |

---

#### 31. `mcp__imo-health__plr___get_study_protocols`

**Description:** Retrieve literature search details, inclusion and exclusion criteria, article types, domain knowledge notes, extraction fields, and protocol links for up to 25 projects.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `project_ids` | array of strings | Yes | Project IDs from `list_projects`. Pass up to 25 per call. |

---

#### 32. `mcp__imo-health__plr___get_screening_counts`

**Description:** Retrieve AI and human screening counts, agreement and disagreement counts, full-text availability counts, and screening and prediction links for up to 25 projects.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `project_ids` | array of strings | Yes | Project IDs from `list_projects`. Pass up to 25 per call. |
| `step` | string enum (`ABSTRACT`, `FULL_TEXT`) | Yes | Screening step: ABSTRACT or FULL_TEXT. |

---

#### 33. `mcp__imo-health__plr___search_citations`

**Description:** Find citations within one project and screening step. Results include citation IDs, publication metadata, AI and human decisions, full-text availability, match totals, and a screening link.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `project_id` | string | Yes | Project ID from `list_projects`. |
| `step` | string enum (`ABSTRACT`, `FULL_TEXT`) | Yes | Screening step: ABSTRACT or FULL_TEXT. |
| `filters` | array of enum values or null | No | Screening decision and full-text availability filters. Values: `AI_IRRELEVANT`, `AI_NOT_SCREENED`, `AI_RELEVANT`, `HUMAN_IRRELEVANT`, `HUMAN_NOT_SCREENED`, `HUMAN_RELEVANT`, `FULL_TEXT_NOT_UPLOADED`, `FULL_TEXT_UPLOADED`. |
| `keyword` | string or null | No | Keyword to match in title, author or journal. |
| `page` | number or null | No | Zero-based page number. |
| `page_size` | number or null | No | Citations per page (1-25). |

---

#### 34. `mcp__imo-health__plr___get_citation_ai_result`

**Description:** Retrieve the AI's predicted study and publication types, screening explanation, and matched exclusion criteria by protocol section for one citation.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `citation_id` | string | Yes | Citation id from search_citations. |
| `step` | string enum (`ABSTRACT`, `FULL_TEXT`) | Yes | Screening step: ABSTRACT or FULL_TEXT. |

---

#### 35. `mcp__imo-health__plr___get_prisma`

**Description:** Retrieve the project's PRISMA flow chart counts and breakdowns for identification, screening, eligibility, and inclusion. The response includes a reporting-page link.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `project_id` | string | Yes | Project ID from `list_projects`. |

---

#### 36. `mcp__imo-health__plr___get_data_summary`

**Description:** Retrieve a page of extracted study data with columns, rows, total row count, study count for the page, sorting details, and a link to the full table.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `project_id` | string | Yes | Project ID from `list_projects`. |
| `page` | number or null | No | Zero-based page number. |
| `page_size` | number or null | No | Rows per page (1-25). |
| `sort_by` | string enum (`PUBLICATION_YEAR`, `TITLE`, `FIRST_AUTHOR`, `JOURNAL`, `PMID`, `DOI`) or null | No | Column to sort by. Defaults to `PUBLICATION_YEAR`. |
| `sort_order` | string enum (`ASCENDING`, `DESCENDING`) or null | No | Sort direction. Defaults to `DESCENDING`. |

---

## Project Structure

**Local Marketplace (Codex CLI):**
```
.mcp.json                    # MCP server config for Codex CLI
.codex-plugin/
  plugin.json                # Codex compatibility manifest
.agents/plugins/
  marketplace.json           # Local marketplace discovery
.app.json                    # MCP server ID mapping (workspace publish)
setup.sh                     # Automated setup script
```

**ChatGPT Plugin ZIP (public submission):**
```
plugin.json                  # Portable plugin manifest
mcp.json                     # MCP server config with OAuth
skills/
  imo-clinical-tools/        # Master tool guide (all 36 tools)
  setup/                     # Installation guide
assets/
  logo.png                   # Plugin logo
  screenshots/               # Plugin screenshots
```

**Shared (used by both):**
```
skills/                      # AI instructions for using MCP tools
assets/                      # Logo and screenshots
```

## Example Queries

Try these after setup:

```
Normalize "type 2 diabetes with kidney disease" and find the most specific ICD-10 code
```

```
Extract all clinical entities from this discharge summary: "Patient presents with chest pain, shortness of breath, and elevated troponin levels"
```

```
What refinements are available for hypertension?
```

```
Map SNOMED code 22298006 to ICD-10-CM
```

```
What procedures are associated with congestive heart failure?
```

## Troubleshooting

### "codex: command not found"
Install Codex CLI:
```bash
npm install -g @openai/codex
```

### MCP server shows "needs authentication"
Run inside Codex:
```
/mcp login IMO-HEALTH-MCP-SERVER
```

### OAuth browser window doesn't open
Restart Codex and try again. Ensure your default browser can be opened from the terminal.

### 401 Unauthorized
Token expired. Codex should auto-refresh. If it doesn't:
```bash
codex mcp remove IMO-HEALTH-MCP-SERVER
```
Then restart Codex — the plugin will re-register the server.

### 429 Too Many Requests
Rate limit hit. Wait and retry. Check the `Retry-After` response header.

### Credentials not working
Verify your environment variables are set:
```bash
echo $IMO_CLIENT_ID
echo $MCP_CLIENT_SECRET
```

## Support

- IMO Health: https://www.imohealth.com
- Developer Portal: https://developer.imohealth.com
