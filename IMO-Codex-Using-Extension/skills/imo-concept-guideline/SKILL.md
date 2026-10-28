---
name: imo-concept-guideline
description: Retrieve ranked IMO concept candidates for clinical terms and search IMO's editorial knowledge base for naming conventions, policies, and migration guidance
when_to_use: Use when the user wants ranked concept candidates with scores for a clinical term, or when they need IMO editorial guidelines on formatting rules, naming conventions, or migration policies. Triggers on words like "concept candidates", "ranked matches", "editorial guidelines", "naming convention", "migration policy", "formatting rules", "acronym rules".
user-invocable: true
---

# Concept Guideline — Candidates & Editorial KB

You are helping the user retrieve ranked concept candidates or search IMO's editorial knowledge base for guidelines and policies.

## Tools

---

### `get_concept_candidates`

Retrieve top-N ranked IMO Clinical Interface Terminology (CIT) candidates for a Problem-domain clinical term. Returns concept IDs paired with word-overlap scores in [0.0, 1.0].

**How this differs from other search/normalize tools:**

| Tool | Returns | Best for |
|------|---------|----------|
| `normalize_ppml_term` | 1 canonical term per input (20 for Medication) | Single best match |
| `search_medical_term` | Ranked results with cross-vocabulary mappings (ICD-10, SNOMED, HCC) | Cross-vocab data |
| **`get_concept_candidates`** | **Top-N candidates with relevance scores** | **Differential lists, ranked options** |

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `term` | `string` | Yes | — | Clinical term to look up (1-1000 chars, e.g., `"chest pain"`) |
| `top_n` | `integer` | No | `10` | Max ranked candidates to return (1-50) |
| `source_type` | `string` | No | `"ICD10"` | Vocabulary label: `"ICD10"`, `"ICD-10-CM"`, `"SNOMED"`, `"SNOMEDCT"`, `"SNOMED-CT"`, or `"IMO"`. Returned concept IDs are always IMO CIT regardless. |

**Response envelope:** `{request_id, term, source_type, candidates:[{concept_id, concept_name, score}], retrieved_count, duration_ms}`

**Example:**
```json
{ "term": "chest pain", "top_n": 5, "source_type": "ICD10" }
```

---

### `search_editorial_kb`

Semantic search over IMO's editorial guideline Knowledge Base. Returns guidance documents — formatting rules, migration policies, naming conventions.

**This is NOT a medical terminology search tool.** It retrieves editorial guidance, such as:

- Policy text (e.g., "how do we treat acronyms in problem titles")
- Migration guidance (e.g., "when moving from ICD-9 to ICD-10-CM, what rules apply")
- Naming conventions (e.g., "should laterality be in the title or a modifier")

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | `string` | Yes | — | Free-text search query (1-1000 chars) |
| `top_n` | `integer` | No | `10` | Max KB chunks to return (1-25) |

**Response envelope:** `{request_id, query, chunks:[{source, score, text}], retrieved_count, duration_ms}`

**Example:**
```json
{ "query": "how should laterality be represented in problem titles", "top_n": 5 }
```

---

## How to Use

### For Ranked Concept Candidates

Use `get_concept_candidates` when the user needs **multiple options with scores** — for example, presenting a differential or choosing between similar concepts:

```json
{ "term": "abdominal pain", "top_n": 10 }
```

Present results sorted by score. The user can then pick the best match and chain to `imo-graphql` for mappings or refinements.

### For Editorial Guidelines

Use `search_editorial_kb` when the user asks about **how IMO content is structured** — not what a clinical term means:

```json
{ "query": "rules for using acronyms in IMO titles", "top_n": 5 }
```

Present the most relevant KB chunks with their source and relevance score.

## Chaining to Other Skills

- **After selecting a candidate** → use `imo-core-search` with `get_term_detail` for full information, or `imo-graphql` for mappings and hierarchy
- **For single canonical normalization** → use `imo-normalize` instead of `get_concept_candidates`
- **For cross-vocabulary search** → use `imo-core-search` with `search_medical_term`
