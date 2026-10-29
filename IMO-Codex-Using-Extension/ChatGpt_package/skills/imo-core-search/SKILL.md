---
name: imo-core-search
description: Search for clinical terms by free text or IMO lexical code and retrieve detailed information including ICD-10, SNOMED, and HCC mappings
when_to_use: Use when the user wants to search for a clinical term, look up a term by its IMO lexical code, or get detailed supplemental information (mapped codes, HCC risk, clinical attributes) for a known code. Triggers on words like "search", "find", "look up", "details for", "what is code".
user-invocable: true
---

# Core Search — Clinical Term Search & Lookup

You are helping the user search for clinical terms and retrieve detailed information using the IMO Core Search API (ProblemIT Professional).

## Tools

This skill uses three tools that form a search → lookup → detail pipeline.

---

### `search_medical_term`

Search for medical terms by free-text query. Returns ranked search results with IMO lexical codes, titles, and mapped codes (ICD-10-CM, SNOMED CT, HCC risk categories).

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `search_term` | `string` | Yes | — | The medical term to search for (e.g., `"chest pain"`, `"diabetes"`). Must not contain `^` or `\|`. |
| `number_of_results` | `integer` | No | `10` | Maximum number of search results to return |

**When to use:** The user provides a free-text clinical term and wants to find matching IMO concepts with their codes.

---

### `lookup_term_by_code`

Look up medical terms by their IMO lexical codes. Returns the search payload for each known code, including the term title, ICD-10-CM/SNOMED mappings, and clinical attributes.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `codes` | `string` | Yes | Comma-separated IMO lexical codes (e.g., `"41884,1056042"`) |

**When to use:** The user already has one or more IMO lexical codes (from normalization or a previous search) and wants the Core Search data for those codes.

---

### `get_term_detail`

Get detailed supplemental information for IMO lexical codes. Returns the full detail payload including mapped codes (ICD-10-CM, SNOMED CT), HCC risk categories, and clinical attributes.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `codes` | `string` | Yes | Comma-separated IMO lexical codes (e.g., `"41884,38195"`) |

**When to use:** The user needs the full detail view — all mapped codes, HCC risk data, and clinical attributes — for specific IMO lexical codes.

---

## How to Use

### Typical Workflow

```
User provides a term
       ↓
  search_medical_term  →  ranked results with lexical codes
       ↓
  get_term_detail      →  full detail for the best match(es)
```

### Step 1: Determine What the User Has

- **Free-text term** (e.g., "chest pain") → use `search_medical_term`
- **IMO lexical code** (e.g., "41884") → use `lookup_term_by_code` or `get_term_detail`
- **Wants full detail on a search result** → use `get_term_detail` with the lexical code from the search

### Step 2: Call the Appropriate Tool

**Free-text search:**
```json
{ "search_term": "chest pain", "number_of_results": 5 }
```

**Code lookup:**
```json
{ "codes": "41884,1056042" }
```

**Full detail:**
```json
{ "codes": "41884" }
```

### Step 3: Present Results

- Show the IMO term title, lexical code, and key mapped codes (ICD-10-CM, SNOMED CT)
- If HCC data is present, highlight the risk categories
- If the user needs more specificity, suggest chaining to `imo-graphql` for hierarchy/refinement exploration

## Chaining to Other Skills

- **Normalize first, then search** → use `imo-normalize` to get the lexical code, then `get_term_detail` here for full detail
- **Map to external code systems** → use `imo-graphql` with `get_mappings` for comprehensive cross-system mapping
- **Explore hierarchy** → use `imo-graphql` with `get_narrower_hierarchy` using the lexical code from search results
- **Extract terms from free text first** → use `imo-nlp` to extract entities, then search/detail each one here

## Examples

**Search by term:**
> "Search for type 2 diabetes"
```json
{ "search_term": "type 2 diabetes", "number_of_results": 10 }
```

**Look up by code:**
> "What is IMO code 41884?"
```json
{ "codes": "41884" }
```

**Get full detail after a search:**
> "Get me the full details for codes 41884 and 38195"
```json
{ "codes": "41884,38195" }
```

**Narrow search results:**
> "Find the top 3 matches for atrial fibrillation"
```json
{ "search_term": "atrial fibrillation", "number_of_results": 3 }
```
