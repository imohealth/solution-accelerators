---
name: imo-nlp
description: Extract clinical entities (problems, medications, labs, allergens) from free-text clinical notes with code mappings to ICD-10-CM, SNOMED, UMLS, and IMO
when_to_use: Use when the user wants to extract structured clinical data from free text such as discharge summaries, progress notes, clinical documentation, or any unstructured medical text. Triggers on words like "extract", "entities", "NLP", "parse note", "clinical note", "discharge summary", "progress note", "find diagnoses in text".
user-invocable: true
---

# NLP — Clinical Entity Extraction

You are helping the user extract structured clinical entities from free-text clinical notes using IMO CCP NLP.

## Tool

### `entity_extraction`

Analyzes clinical text to identify medical entities with semantic information and code mappings.

**What it extracts:**
- **Problems** — diagnoses, conditions, symptoms, findings
- **Medications** — drugs, prescriptions, dosages
- **Labs** — lab tests, results, panels
- **Allergens** — drug and non-drug allergies

**Code systems mapped:**
- ICD-10-CM
- SNOMED CT
- UMLS
- IMO

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `text` | `string` | Yes | — | Clinical text to extract entities from (e.g., discharge summary, progress note) |
| `version` | `string` | No | `"3.0"` | API version |

## How to Use

### Step 1: Get the Clinical Text

The user provides clinical free text — this could be:
- A discharge summary
- A progress note
- An operative report
- An H&P (history and physical)
- Any clinical documentation

### Step 2: Call the Tool

Pass the full text to the tool. The NLP engine handles segmentation internally.

```json
{
  "text": "Patient presents with acute chest pain radiating to left arm. History of type 2 diabetes mellitus and hypertension. Currently on metformin 500mg BID and lisinopril 10mg daily. CBC and BMP ordered. Known allergy to penicillin.",
  "version": "3.0"
}
```

### Step 3: Present Results

Organize extracted entities by type:

- **Problems found:** list each with its ICD-10, SNOMED, and IMO codes
- **Medications found:** list each with dosage and code mappings
- **Labs found:** list each with code mappings
- **Allergens found:** list each with details

### Step 4: Suggest Next Steps

After extraction, the user may want to:

- **Normalize** extracted terms for higher precision → chain to `imo-normalize`
- **Get detailed information** on extracted codes → chain to `imo-core-search`
- **Map to other code systems** → chain to `imo-graphql` with `get_mappings`
- **Refine specificity** of extracted diagnoses → chain to `imo-graphql` with hierarchy/refinement tools
- **Categorize** the extracted problem list → chain to `imo-categorize`

## Chaining to Other Skills

| After extraction, if the user wants to... | Use |
|-------------------------------------------|-----|
| Normalize terms to IMO standard | `imo-normalize` |
| Get full detail on a code | `imo-core-search` → `get_term_detail` |
| Map to ICD-10 / SNOMED / CPT | `imo-graphql` → `get_mappings` |
| Find more specific codes | `imo-graphql` → `get_narrower_hierarchy` + refinements |
| Group problems by disease area | `imo-categorize` |
| Find treatments for a problem | `imo-graphql` → `get_cross_domain` |

## Examples

**Short clinical note:**
> "Extract entities from: Patient has COPD with acute exacerbation, on albuterol nebulizer."
```json
{
  "text": "Patient has COPD with acute exacerbation, on albuterol nebulizer.",
  "version": "3.0"
}
```

**Discharge summary:**
> "Parse this discharge summary for diagnoses and medications: [full text]"
```json
{
  "text": "<full discharge summary text>",
  "version": "3.0"
}
```

**Extract and then categorize:**
> "Extract all problems from this note and group them by disease area"
1. First call `entity_extraction` to get the problems
2. Then chain to `imo-categorize` with `categorize_problems` using the extracted problem list
