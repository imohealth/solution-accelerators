---
name: imo-clinical-tools
description: Comprehensive guide to all 19 IMO Health MCP tools — helps the agent pick the right tool for any clinical terminology question.
---

# IMO Health Clinical Intelligence — Tool Guide

This skill teaches you how to use all 19 IMO Health MCP tools. Use this guide to pick the correct tool(s) for any user request about clinical terminology, medical coding, normalization, or knowledge graph exploration.

## Decision Tree — Which Tool to Use

| User wants to... | Use this tool |
|---|---|
| Normalize a medical term | `normalize_ppml___normalize_ppml_term` |
| Search for a medical term | `core_search___search_medical_term` |
| Get multiple ranked candidates for a term | `concept_guideline___get_concept_candidates` |
| Get ICD-10, SNOMED, CPT mappings | `graphql_modifier___get_mappings` |
| Get detailed info on a term | `core_search___get_term_detail` |
| Look up a term by its code | `core_search___lookup_term_by_code` |
| See hierarchy (parents/children) | `graphql_modifier___get_narrower_hierarchy` |
| See what refinements are available | `graphql_modifier___get_allowed_refinements` |
| See all options in a refinement group | `graphql_modifier___get_refinement_group` |
| Apply refinements to drill deeper | `graphql_modifier___get_narrower_sequential_refinements` |
| Filter children by a refinement | `graphql_modifier___get_narrower_with_refinements` |
| Get full lexical details | `graphql_modifier___get_lexical` |
| Find related procedures/medications | `graphql_modifier___get_cross_domain` |
| Find what problems a drug/procedure treats | `graphql_modifier___get_related_problems` |
| Extract entities from clinical text | `ccp___entity_extraction` |
| Categorize a problem list | `categorize___categorize_problems` |
| Look up editorial/naming guidelines | `concept_guideline___search_editorial_kb` |
| Explore the KG schema | `knowledge_graph_explorer___explore_schema` |
| Run a SPARQL query | `knowledge_graph_explorer___run_sparql` |

---

## Tool Reference — All 19 Tools

### 1. Normalize

#### `normalize_ppml___normalize_ppml_term`
Normalize medical terms to IMO lexical codes using the Precision Normalize API.

- **Domains**: Problem, Procedure, Medication, Lab
- **Returns**: 1 result per term (Problem/Procedure/Lab), 20 results per term (Medication)
- **Key output**: `lexical_code` — use this (NOT `imo_code`) as input to all Knowledge Graph tools
- **When to use**: Starting point for most workflows. User provides a medical term in plain text and needs the standardized IMO code.

---

### 2. Core Search (3 tools)

#### `core_search___search_medical_term`
Search for medical terms using ranked results with IMO lexical codes, titles, and mapped codes (ICD-10-CM, SNOMED CT, HCC risk).

- **When to use**: User wants to search/browse terms rather than normalize a specific term. Returns multiple ranked results.
- **Output**: IMO lexical codes, titles, mapped codes. Use returned codes with `get_term_detail` or `get_lexical`.

#### `core_search___get_term_detail`
Get detailed supplemental information for IMO lexical codes.

- **Input**: IMO lexical codes (from `search_medical_term` or `normalize_ppml_term`)
- **Returns**: Full detail payload including mapped codes (ICD-10-CM, SNOMED CT), HCC risk categories, clinical attributes.
- **When to use**: User needs deeper info beyond what search/normalize returns.

#### `core_search___lookup_term_by_code`
Look up medical terms when you already have IMO lexical codes.

- **Input**: Known IMO lexical codes
- **Returns**: Term title, ICD-10-CM/SNOMED mappings, clinical attributes
- **When to use**: You already have a lexical code and need the Core Search data for it.

---

### 3. Knowledge Graph — Mappings & Lexical (2 tools)

#### `graphql_modifier___get_mappings`
Retrieve external code mappings for an IMO lexical from the Knowledge Graph.

- **IMPORTANT**: Use `lexical_code` (NOT `imo_code`) as input.
- **Problem domain**: ICD-10-CM, ICD-10-CA, ICD-9-CM, SNOMED CT, DSM-5, ICD-O, MONDO. Set `include_hcc=True` for HCC risk data.
- **Procedure domain**: CPT, HCPCS, ICD-10-PCS, LOINC, SNOMED CT.
- **Medication domain**: RxNorm (with term-type), NDC (brand/generic, dosage, route, ingredients), CVX (vaccine status), SNOMED CT.
- **Relationship types**: exactMatch, closeMatch, broadMatch, narrowMatch, relatedMatch.
- **When to use**: User asks "What's the ICD-10 for X?", "Map this to SNOMED", "What's the CPT code?", or any cross-code mapping.

#### `graphql_modifier___get_lexical`
Look up an IMO lexical by its code in the Knowledge Graph.

- **IMPORTANT**: Use `lexical_code` (NOT `imo_code`) as input.
- **Returns**: Title, broader (parent) concepts, applied refinements (already in the lexical), allowed refinements grouped by category.
- **Note**: Applied and allowed refinements are Problem domain only.
- **When to use**: Need the full KG context for a lexical — parents, what refinements are already applied, what further refinements are possible.

---

### 4. Knowledge Graph — Refinements (3 tools)

#### `graphql_modifier___get_allowed_refinements`
Look up what refinements (modifiers) can be applied to make an IMO Problem lexical more specific.

- **IMPORTANT**: Use `lexical_code` (NOT `imo_code`). Problem domain only.
- **Returns**: Refinement groups and options (e.g., laterality, chronicity, severity, location).
- **When to use**: User asks "How can I make this more specific?", "What modifiers are available?", or you need to drill down a diagnosis.

#### `graphql_modifier___get_refinement_group`
Look up all options within a specific refinement group.

- **Input**: Group code from `get_allowed_refinements` or `get_lexical` results.
- **Returns**: All possible values in that group (e.g., laterality → right, left, bilateral, unilateral, unspecified).
- **When to use**: User wants to see all options for a specific modifier type.

#### `graphql_modifier___get_narrower_sequential_refinements`
Apply multiple refinements as a nested sequence to drill down to the most specific lexical.

- **IMPORTANT**: Use `lexical_code` (NOT `imo_code`). Problem domain only.
- **Input**: `refinement_sequence` — array of arrays, each level creates a deeper traversal.
- **Set `include_mappings: true`** to get ICD-10 codes at the deepest level.
- **Set `include_allowed_refinements: true`** to check if further refinement is possible.
- **When to use**: Applying multiple refinement steps at once (e.g., laterality → right, then chronicity → acute). This is the key tool for diagnosis specificity workflows.

---

### 5. Knowledge Graph — Hierarchy & Filtering (2 tools)

#### `graphql_modifier___get_narrower_hierarchy`
Explore the hierarchy of an IMO lexical — one level up (parents) and one level down (children).

- **IMPORTANT**: Use `lexical_code` (NOT `imo_code`). Problem domain only.
- **Returns**: Broader (parent) and narrower (child) lexicals. Results are paged.
- **When to use**: User asks "What's above/below this?", "Show me the hierarchy", or browsing the taxonomy.
- **Navigation**: Call again with a child's code to walk deeper.

#### `graphql_modifier___get_narrower_with_refinements`
Get narrower lexicals filtered by specific refinement criteria.

- **IMPORTANT**: Use `lexical_code` (NOT `imo_code`). Problem domain only.
- **Returns**: Only children matching the given refinement codes. Results are paged.
- **When to use**: User wants filtered children (e.g., "Show me all knee pain variants with laterality:right").

---

### 6. Knowledge Graph — Cross-Domain (2 tools)

#### `graphql_modifier___get_cross_domain`
Discover cross-domain clinical relationships for an IMO Problem lexical.

- **IMPORTANT**: Use `lexical_code` (NOT `imo_code`).
- **Returns relationships across domains**:
  - Associated findings / procedures / lab procedures
  - Treatments (primary) + supportive medications
  - Causative agents and due-to causes (etiology)
  - Temporally-related concepts (during / after / before)
  - Realizations, finding methods, routine lab procedures, interpreted procedures
- **Results are paged** — some relationships are very large (six figures). Use `offset` to page.
- **When to use**: User asks "What treats this?", "What causes this?", "What procedures are associated?", "What medications are used for this?"

#### `graphql_modifier___get_related_problems`
Reverse lookup — find problems related to a procedure or medication.

- **IMPORTANT**: Use `lexical_code` (NOT `imo_code`).
- **Procedure input returns**: associatedProblems, interpretedFindings, determinedProblems, causedProblems, realizedProblems.
- **Medication input returns**: treatedProblems, causedProblems.
- **Results are paged** — can be very large.
- **When to use**: User asks "What problems does this drug treat?", "What conditions is this procedure for?"

---

### 7. NLP & Categorization (2 tools)

#### `ccp___entity_extraction`
Extract clinical entities from free text using IMO CCP NLP.

- **Input**: Any clinical text (discharge summary, progress note, consultation report).
- **Returns**: Entities classified as Problems, Medications, Labs, Allergens — with code mappings to ICD-10-CM, SNOMED, UMLS, IMO.
- **When to use**: User provides clinical narrative text and wants structured entities extracted.

#### `categorize___categorize_problems`
Organize a list of clinical problems into disease categories.

- **Input**: List of clinical problems.
- **Returns**: Problems grouped by disease category.
- **When to use**: User has a long problem list and wants it organized/decluttered for chart review or clinical summary.

---

### 8. Concept Guideline (2 tools)

#### `concept_guideline___get_concept_candidates`
Retrieve top-N ranked IMO CIT candidates for a Problem-domain term.

- **Returns**: Multiple ranked candidates with retrieval scores [0.0, 1.0]. Problem domain only.
- **Different from normalize**: Normalize returns 1 canonical result; this returns top-N with scores.
- **Different from search**: Search returns cross-vocabulary mappings; this returns Problem-domain IMO CIT only.
- **When to use**: User needs a differential list of candidates (e.g., "what are the possible matching concepts for this term?").

#### `concept_guideline___search_editorial_kb`
Semantic search over IMO's editorial guideline Knowledge Base.

- **NOT a medical terminology tool** — retrieves editorial guidance documents.
- **Returns**: Policy text, migration guidance, naming conventions.
- **Examples**: "How do we treat acronyms in problem titles?", "ICD-9 to ICD-10-CM migration rules", "Should laterality be in the title or a modifier?"
- **When to use**: Questions about IMO content authoring rules, formatting policies, or migration guidance.

---

### 9. SPARQL / Schema Explorer (2 tools)

#### `knowledge_graph_explorer___explore_schema`
Discover the shape of the IMO Knowledge Graph before writing a SPARQL query.

- **Returns**: Named graphs (urn:x-imo:problem, procedure, subrx, modifier), classes with instance counts, predicates with usage counts, sample triples for a class.
- **When to use**: ALWAYS run this before `run_sparql`. Grounds your query in actual schema instead of guessing.

#### `knowledge_graph_explorer___run_sparql`
Execute a read-only SPARQL query against the IMO Knowledge Graph.

- **Call `explore_schema` first** to know the graphs, classes, and predicates.
- **Allowed**: SELECT, ASK, CONSTRUCT, DESCRIBE only. Write operations are rejected.
- **Auto-limit**: A default LIMIT is injected into bare SELECTs.
- **When to use**: Advanced users who need custom queries beyond what the other tools provide.

---

## Common Workflows

### Normalize and Map
1. `normalize_ppml___normalize_ppml_term` → get `lexical_code`
2. `graphql_modifier___get_mappings` → get ICD-10, SNOMED, etc.

### Diagnosis Specificity
1. `normalize_ppml___normalize_ppml_term` → get `lexical_code`
2. `graphql_modifier___get_allowed_refinements` → see available modifiers
3. `graphql_modifier___get_narrower_sequential_refinements` → apply refinements, drill down
4. `graphql_modifier___get_mappings` → get final ICD-10 at most specific level

### Entity Extraction + Enrichment
1. `ccp___entity_extraction` → extract entities from text
2. `normalize_ppml___normalize_ppml_term` → normalize each entity
3. `graphql_modifier___get_mappings` → get code mappings

### Cross-Code Mapping
1. `core_search___lookup_term_by_code` or `core_search___search_medical_term` → find IMO lexical
2. `graphql_modifier___get_mappings` → get target code system mappings

### Explore Relationships
1. `normalize_ppml___normalize_ppml_term` → get `lexical_code`
2. `graphql_modifier___get_cross_domain` → find related procedures, meds, causes
3. `graphql_modifier___get_related_problems` → reverse lookup from procedure/medication

## Output Formatting

Always present results in a clean, structured, and well-formatted way:

- **Lead with identity** — Start with the IMO lexical ID, term title, and domain (e.g., "IMO lexical ID 85191 — Chest pain")
- **Use counts** — State the total count upfront (e.g., "has 14 available refinement options")
- **Group by category** — Organize results under their group name (e.g., "Chest pain type:", "Ischemic chest pain type:")
- **Bullet lists** — Each option on its own bullet line under each group, one option per line
- **Tables for mappings** — Present ICD-10, SNOMED, CPT mappings in a table format
- **Numbered steps for workflows** — When walking through multi-step tool chains, number each step
- **End with guidance** — Add a note like "Use only the option supported by the documented clinical details"
- **Keep it scannable** — Use bold, headers, and whitespace to make results easy to read
- **Show all returned data** — Never hide or skip fields from tool responses. Display every piece of data the tool returns (codes, titles, mappings, scores, domains, relationships) in a well-structured format. If the API returns it, the user should see it.
- **Always include codes with names** — When listing refinements, options, or any clinical concepts, always show their associated codes (lexical code, ICD-10, SNOMED, etc.) alongside the name. Never show just the name without codes. Use `include_mappings: true` when available to fetch codes.
- **Use table format for lists** — Present refinements, mappings, and multi-field results as a markdown table. For refinements use columns: Refinement group | Group code | Option | IMO refinement code. For mappings use columns: Code System | Code | Description | Match Type. Always include all codes returned by the tool.
- **Suggest next questions** — After every response, suggest 5 follow-up questions the user can ask based on the current result

## Critical Rules

- **Stay on task.** Only perform what the user explicitly asked for. Do not run extra tools, add unrequested analysis, or expand the scope beyond the user's request. If the user asks to normalize a term, normalize it — do not also map it, refine it, or explore relationships unless asked.
- **Don't invent clinical data.** Never fabricate codes, mappings, or clinical relationships. If a tool returns no results, say so — do not guess or fill in values.
- **Show your source.** Always include the tool name and the actual values returned. Do not paraphrase or summarize code mappings — present them exactly as the tool returned them.
- **Always use `lexical_code`, NEVER `imo_code`** as input to Knowledge Graph tools.
- Refinement tools (`get_allowed_refinements`, `get_narrower_*`) work only in the **Problem domain**.
- Cross-domain tools work across Problem, Procedure, and Medication domains.
- Large result sets are **paged** — use `offset` to retrieve more.
- Always remind users: confirm results against clinical documentation and organizational coding policies.
