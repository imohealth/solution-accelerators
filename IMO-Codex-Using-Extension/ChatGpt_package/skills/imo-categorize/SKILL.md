---
name: imo-categorize
description: Organize clinical problem lists into intuitive disease categories for chart review, clinical summaries, and specialty-based grouping
when_to_use: Use when the user wants to group, categorize, or organize a list of clinical problems by disease area or specialty. Triggers on words like "categorize", "group problems", "organize problem list", "disease categories", "sort by specialty", "declutter problem list".
user-invocable: true
---

# Categorize — Problem List Organization

You are helping the user organize clinical problem lists into intuitive disease categories using IMO's clinical intelligence.

## Tool

### `categorize_problems`

Groups related clinical conditions together to declutter problem lists. Useful for patient chart review and clinical summaries.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `problems` | `array[object]` | Yes | — | List of problems to categorize. Each problem is an object with keys: `id`, `title`, `lexical_code`, `icd10`, `snomed`. At least one of `title`, `icd10`, or `snomed` is required. |
| `priority_specialty` | `string` or `null` | No | `null` | Optional provider specialty code to prioritize in category ordering |

## How to Use

### Step 1: Build the Problem List

Each problem in the array needs at minimum one of:
- `title` — the clinical problem name (e.g., "Type 2 diabetes mellitus")
- `icd10` — an ICD-10-CM code (e.g., "E11.9")
- `snomed` — a SNOMED CT code

Optional fields: `id` (your own identifier), `lexical_code` (IMO lexical code for higher precision).

### Step 2: Call the Tool

```json
{
  "problems": [
    { "id": "1", "title": "Type 2 diabetes mellitus", "icd10": "E11.9" },
    { "id": "2", "title": "Essential hypertension", "icd10": "I10" },
    { "id": "3", "title": "Chronic kidney disease stage 3", "icd10": "N18.3" },
    { "id": "4", "title": "Major depressive disorder", "icd10": "F33.0" },
    { "id": "5", "title": "Obesity", "icd10": "E66.9" },
    { "id": "6", "title": "Hyperlipidemia", "icd10": "E78.5" }
  ],
  "priority_specialty": null
}
```

### Step 3: Present Results

Show the categorized groups clearly — for example:

- **Endocrine/Metabolic:** Type 2 diabetes mellitus, Obesity, Hyperlipidemia
- **Cardiovascular:** Essential hypertension
- **Renal:** Chronic kidney disease stage 3
- **Psychiatric:** Major depressive disorder

### Using `priority_specialty`

If the user specifies a specialty, pass it as `priority_specialty` to influence category ordering. The categories from that specialty will appear first in the results.

## Input Formats

**With titles only (simplest):**
```json
{
  "problems": [
    { "id": "1", "title": "Type 2 diabetes mellitus" },
    { "id": "2", "title": "Essential hypertension" }
  ]
}
```

**With ICD-10 codes only:**
```json
{
  "problems": [
    { "id": "1", "icd10": "E11.9" },
    { "id": "2", "icd10": "I10" }
  ]
}
```

**With full detail (best precision):**
```json
{
  "problems": [
    { "id": "1", "title": "Type 2 diabetes mellitus", "lexical_code": "38195", "icd10": "E11.9", "snomed": "44054006" }
  ]
}
```

## Chaining from Other Skills

| If the user starts with... | Chain |
|----------------------------|-------|
| A clinical note (free text) | `imo-nlp` → extract problems → `categorize_problems` |
| Raw term names | `imo-normalize` → get codes → `categorize_problems` |
| IMO lexical codes | `imo-core-search` → get titles/codes → `categorize_problems` |

## Examples

**Direct categorization:**
> "Categorize these problems: diabetes, hypertension, COPD, depression, chronic kidney disease"
Build the problem list with titles and call `categorize_problems`.

**Extract then categorize:**
> "Extract all diagnoses from this note and group them by disease area"
1. Call `imo-nlp` → `entity_extraction` on the note
2. Build the problem list from extracted entities
3. Call `categorize_problems` with the list

**Specialty-prioritized:**
> "Group this problem list with cardiology problems first"
```json
{
  "problems": [ ... ],
  "priority_specialty": "cardiology"
}
```
