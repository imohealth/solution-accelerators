---
name: imo-normalize
description: Normalize clinical terms to standard IMO terminology across Problem, Procedure, Medication, and Lab domains using Precision Normalize (PPML)
when_to_use: Use when the user wants to normalize, standardize, or map a free-text clinical term to IMO's standard clinical terminology. Triggers on words like "normalize", "standardize", "map term", "what's the standard name for", or when a raw clinical term needs to be resolved to an IMO concept.
user-invocable: true
---

# Normalize Clinical Terms

You are helping the user normalize free-text clinical terms to IMO's standard clinical terminology using the Precision Normalize API.

## Tool

### `normalize_ppml_term`

Normalize medical terms using the IMO Precision Normalize API across Problem, Procedure, Medication, and Lab domains.

- For **Medication** domain: returns **20 results** per term
- For **Problem**, **Procedure**, and **Lab** domains: returns **1 result** per term

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `terms` | `array[string]` | Yes | List of medical terms to normalize (e.g., `["diabetes", "chest pain", "amoxicillin", "CBC"]`) |
| `domain` | `string` | Yes | Must be one of: `"Problem"`, `"Procedure"`, `"Medication"`, `"Lab"` |

## How to Use

### Step 1: Determine the Domain

Based on the user's input, pick the correct domain:

- **Problem** — diagnoses, conditions, symptoms, findings (e.g., "chest pain", "diabetes", "hypertension")
- **Procedure** — surgical or diagnostic procedures (e.g., "colonoscopy", "MRI brain", "appendectomy")
- **Medication** — drugs, prescriptions (e.g., "amoxicillin", "metformin", "lisinopril")
- **Lab** — lab tests, panels (e.g., "CBC", "BMP", "hemoglobin A1c")

If the domain is ambiguous, ask the user. If the user provides a mixed list, split them by domain and make separate calls.

### Step 2: Call the Tool

```json
{
  "terms": ["chest pain", "shortness of breath"],
  "domain": "Problem"
}
```

**Important:** The `domain` value must be capitalized exactly: `"Problem"`, `"Procedure"`, `"Medication"`, or `"Lab"`.

### Step 3: Interpret Results

The response includes:

- **`imo_code`** — the internal IMO concept identifier
- **`lexical_code`** — the IMO lexical code used as input for Knowledge Graph tools
- **`title`** — the standardized IMO term name
- **Mapped codes** — ICD-10-CM, SNOMED CT, and other mappings depending on domain

**Critical distinction:** When chaining to other tools (GraphQL, Knowledge Graph), always use the `lexical_code`, NOT the `imo_code`.

## Chaining to Other Skills

After normalization, the user may want to:

- **Get full details** → use `imo-core-search` with the returned lexical codes via `get_term_detail`
- **Map to other code systems** → use `imo-graphql` with `get_mappings` using the `lexical_code`
- **Explore hierarchy / refine specificity** → use `imo-graphql` with `get_narrower_hierarchy` or `get_allowed_refinements`
- **Find cross-domain relationships** → use `imo-graphql` with `get_cross_domain`

## Examples

**Single term:**
> "Normalize heart attack"
```json
{ "terms": ["heart attack"], "domain": "Problem" }
```

**Multiple terms, same domain:**
> "Standardize amoxicillin, metformin, and lisinopril"
```json
{ "terms": ["amoxicillin", "metformin", "lisinopril"], "domain": "Medication" }
```

**Mixed domains — split into separate calls:**
> "Normalize diabetes, colonoscopy, and CBC"
- Call 1: `{ "terms": ["diabetes"], "domain": "Problem" }`
- Call 2: `{ "terms": ["colonoscopy"], "domain": "Procedure" }`
- Call 3: `{ "terms": ["CBC"], "domain": "Lab" }`
