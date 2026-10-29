---
name: imo-graphql
description: Navigate the IMO Knowledge Graph via GraphQL — code mappings, hierarchy traversal, refinements, cross-domain relationships, and reverse lookups
when_to_use: Use when the user wants to map codes across systems (ICD-10, SNOMED, CPT, RxNorm, NDC), explore parent/child hierarchies, apply refinements (laterality, chronicity, etc.), find cross-domain relationships (treatments, procedures, causative agents), or do reverse lookups from procedures/medications to problems. Triggers on words like "map", "cross-map", "hierarchy", "children", "parent", "refine", "laterality", "specificity", "related problems", "treatments for", "what procedures".
user-invocable: true
---

# GraphQL Modifier — Knowledge Graph Navigation

You are helping the user navigate the IMO Health Knowledge Graph via GraphQL. This skill covers code mappings, hierarchy traversal, refinements, cross-domain relationships, and reverse lookups.

**Critical:** All tools in this skill require the `lexical_code` from normalization or search results — NOT the `imo_code`. If the user only has a free-text term, chain from `imo-normalize` or `imo-core-search` first.

## Tools

This skill has 9 tools organized into four sub-sections.

---

## A. Code Mappings

### `get_mappings`

Retrieve external code mappings for an IMO lexical. Returns equivalent codes in standard coding systems with relationship types (exactMatch, closeMatch, broadMatch, narrowMatch, relatedMatch).

**Available code systems by domain:**
- **problem:** `icd10cm`, `icd10ca`, `icd9cm`, `snomedInternational`, `snomedCa`, `snomedUs`, `dsm5`, `icdO`, `mondo`
- **procedure:** `cpt`, `hcpcs`, `icd10pcs`, `loinc`, `snomedInternational`
- **medication:** `rxnorm`, `ndc`, `cvx`, `snomedInternational`

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `imo_lexical_code` | `string` | Yes | — | The `lexical_code` from normalize/search results |
| `domain` | `string` | No | `"problem"` | `"problem"`, `"procedure"`, or `"medication"` |
| `code_systems` | `array[string]` or `null` | No | `null` | Filter by specific code systems. If null, returns all. |
| `include_hcc` | `boolean` | No | `false` | Problem domain only. Adds HCC data (category, description, model) on ICD-10-CM mappings. |

**Example:**
```json
{
  "imo_lexical_code": "78845",
  "domain": "problem",
  "code_systems": ["icd10cm", "snomedUs"],
  "include_hcc": true
}
```

---

## B. Lexical Lookup & Hierarchy

### `get_lexical`

Look up an IMO lexical by code. Returns the title, broader (parent) concepts, applied refinements, and allowed refinements grouped by category.

**Note:** `appliedRefinements` and `allowedRefinements` are only available for the `"problem"` domain.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `imo_lexical_code` | `string` | Yes | — | The `lexical_code` from normalize/search results |
| `domain` | `string` | No | `"problem"` | `"problem"`, `"procedure"`, or `"medication"` |

**Example:**
```json
{ "imo_lexical_code": "85191", "domain": "problem" }
```

---

### `get_narrower_hierarchy`

Explore one level up (broader/parents) and one level down (narrower/children) from a concept. Call again with a child or parent code to walk further.

**Note:** Problem hierarchy (`domainBroader`/`domainNarrower`) is only available for the `"problem"` domain. Results are paged — 100 items per level.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `imo_lexical_code` | `string` | Yes | — | The `lexical_code` from normalize/search results |
| `domain` | `string` | No | `"problem"` | The lexical domain |
| `offset` | `integer` | No | `0` | Zero-based paging offset (100 broader + 100 narrower per call) |

**Example:**
```json
{ "imo_lexical_code": "78845", "domain": "problem", "offset": 0 }
```

---

## C. Refinements

### `get_allowed_refinements`

Look up what refinements (modifiers) can make a concept more specific — laterality, chronicity, location, severity, etc. Each refinement has a group code and title.

**Note:** Only available for the `"problem"` domain. Results are paged — 100 per call.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `imo_lexical_code` | `string` | Yes | — | The `lexical_code` from normalize/search results |
| `domain` | `string` | No | `"problem"` | The lexical domain |
| `offset` | `integer` | No | `0` | Zero-based paging offset |

**Example:**
```json
{ "imo_lexical_code": "78845", "domain": "problem" }
```

---

### `get_refinement_group`

Look up all options within a specific refinement category. For example, get all laterality options: right, left, bilateral, unilateral, unspecified.

Get the group `notation` from the `group.code` field in `get_allowed_refinements` or `get_lexical` results.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `notation` | `string` | Yes | The refinement group notation/code (e.g., `"149"` for laterality) |

**Example:**
```json
{ "notation": "149" }
```

---

### `get_narrower_with_refinements`

Filter narrower (more specific) concepts by specific refinement codes. Use after `get_allowed_refinements` to find children matching a refinement (e.g., all knee pain variants with laterality:right).

**Note:** Only available for `"problem"` domain. Results are paged — 100 per call.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `imo_lexical_code` | `string` | Yes | — | The `lexical_code` from normalize/search results |
| `refinement_codes` | `array[string]` | Yes | — | List of refinement codes to filter by (e.g., `["230"]` for laterality:right) |
| `domain` | `string` | No | `"problem"` | The lexical domain |
| `offset` | `integer` | No | `0` | Zero-based paging offset |

**Example:**
```json
{
  "imo_lexical_code": "78845",
  "refinement_codes": ["230"],
  "domain": "problem"
}
```

---

### `get_narrower_sequential_refinements`

Apply multiple refinement levels as a single nested query. Each level in the `refinement_sequence` creates a deeper `narrower()` call. Maximum 3 levels deep.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `imo_lexical_code` | `string` | Yes | — | The starting `lexical_code` |
| `refinement_sequence` | `array[array[string]]` | Yes | — | Ordered sequence of refinement code lists — max 3 levels (e.g., `[["230"], ["362636588"]]`) |
| `domain` | `string` | No | `"problem"` | The lexical domain |
| `include_allowed_refinements` | `boolean` | No | `false` | Include `allowedRefinements` at every nesting level |
| `include_mappings` | `boolean` | No | `false` | Include code mappings at the deepest level |

**Example:**
```json
{
  "imo_lexical_code": "601056",
  "refinement_sequence": [["230"], ["362636588"]],
  "include_allowed_refinements": true,
  "include_mappings": true
}
```

---

## D. Cross-Domain Relationships

### `get_cross_domain`

From a **problem**, discover related concepts across other domains: associated procedures, medications, findings, treatments, causative agents, temporal relationships, and more.

Results are paged — 100 items per relationship per call. Use `totals` and `truncated` in the response to decide whether to page further with `offset`.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `imo_lexical_code` | `string` | Yes | — | The `lexical_code` of a **problem** |
| `offset` | `integer` | No | `0` | Zero-based paging offset (100 items per relationship per call) |

**Relationships returned:**
- Associated findings, procedures, lab procedures
- Treatments (primary) and supportive medications
- Causative agents and due-to causes (etiology)
- Temporally-related concepts (during / after / before)
- Realizations, finding methods, routine lab procedures, interpreted procedures

**Example:**
```json
{ "imo_lexical_code": "41297", "offset": 0 }
```

---

### `get_related_problems`

Reverse lookup: from a **procedure** or **medication**, find the problems that reference it.

- **procedure:** returns `associatedProblems`, `interpretedFindings`, `determinedProblems`, `causedProblems`, `realizedProblems`
- **medication:** returns `treatedProblems`, `causedProblems`

Results are paged — 100 per call. These relationships can be very large (six figures for common medications).

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `imo_lexical_code` | `string` | Yes | — | The `lexical_code` of a procedure or medication |
| `domain` | `string` | No | `"procedure"` | `"procedure"` or `"medication"` |
| `offset` | `integer` | No | `0` | Zero-based paging offset (100 items per call) |

**Example:**
```json
{ "imo_lexical_code": "123456", "domain": "medication", "offset": 0 }
```

---

## Common Workflows

### Diagnostic Specificity (most common)

```
normalize term (imo-normalize)
  → get_lexical (see current refinements)
  → get_allowed_refinements (see what's available)
  → get_narrower_with_refinements (filter by selected refinement)
  → get_mappings (get final ICD-10/SNOMED codes)
```

### Cross-System Code Mapping

```
normalize term (imo-normalize)
  → get_mappings (with code_systems filter)
```

### "What treats this condition?"

```
normalize problem (imo-normalize)
  → get_cross_domain (look at treatments and supportive medications)
```

### "What does this medication treat?"

```
normalize medication (imo-normalize)
  → get_related_problems (domain: "medication")
```

## Chaining to Other Skills

- **Need a lexical_code first?** → use `imo-normalize` or `imo-core-search`
- **Need to extract terms from text?** → use `imo-nlp` first, then use lexical codes here
- **Need SPARQL queries?** → use `imo-knowledge-graph-explorer` for direct graph access
