<img src="../static/imo_health.png" alt="IMO Health Logo" width="300"/>

---

# Clinical NLP — Entity Extraction, Categorize & Clean

**Products:** IMO Clinical AI · IMO Problem List Management

This folder contains a three-notebook workflow that takes a free-text clinical note, extracts structured clinical entities, groups them by specialty, and cleans the resulting problem list for duplicates and stale conditions.

---

## Notebooks

### 1. `01_IMO_Entity_Extraction.ipynb`
**Product:** IMO Clinical AI

Submits a raw clinical narrative (e.g. a SOAP note) to the IMO Entity Extraction API and returns a list of coded clinical entities.

What it does:
- Installs dependencies and loads `entity_extraction` credentials from `config.json`
- Authenticates with the IMO OAuth endpoint
- POSTs a clinical note to the `imo-clinical-comprehensive` pipeline
- Parses each entity's `text`, `semantic` type, and `assertion` status (`present`, `negated`, `historical`, etc.)
- Expands `codemaps` to surface ICD-10-CM, SNOMED-CT, RxNorm, CPT, and LOINC codes per entity
- Filters to clinically relevant assertions and exports `extracted_entities` for use in Notebooks 2 & 3

---

### 2. `02_IMO_Problem_List_Categorize.ipynb`
**Product:** IMO Problem List Management

Groups a patient's problem list into clinical specialty categories.

What it does:
- Loads `problem_list` credentials and authenticates
- Accepts `extracted_entities` from Notebook 1 (same kernel session), or falls back to a built-in sample problem list
- POSTs the problem list to the IMO Categorize endpoint
- Parses `categories[]` — each with a specialty code, title, and member problems
- Displays a specialty breakdown DataFrame and a problem-count summary table

---

### 3. `03_IMO_Problem_List_Clean.ipynb`
**Product:** IMO Problem List Management

Identifies redundant, stale, and clinically related problems in a patient's problem list.

What it does:
- Loads `problem_list` credentials and authenticates
- Accepts `extracted_entities` from Notebook 1 (same kernel session), or falls back to a built-in sample list that includes intentional duplicates and related conditions
- POSTs the problem list to the IMO Clean endpoint
- Parses and displays all four response groups:
  - `acute` — currently active problems
  - `lapsed` — problems no longer clinically active
  - `duplicates` — problems representing the same condition
  - `related` — problems that are clinically related to each other
- Produces a consolidated summary table showing which clean groups each problem belongs to

---

## Recommended Run Order

1. Run Notebook 1 to extract and code entities from a clinical note
2. Run Notebook 2 to categorize the resulting problem list by specialty
3. Run Notebook 3 to clean the problem list for duplicates and lapsed conditions

Notebooks 2 and 3 can also be run standalone using their built-in sample data.

---

## Configuration

Copy `config.json.template` to `config.json` and fill in your credentials:

```json
{
  "entity_extraction": {
    "client_id": "YOUR_ENTITY_EXTRACTION_CLIENT_ID",
    "client_secret": "YOUR_ENTITY_EXTRACTION_CLIENT_SECRET"
  },
  "problem_list": {
    "client_id": "YOUR_PROBLEM_LIST_CLIENT_ID",
    "client_secret": "YOUR_PROBLEM_LIST_CLIENT_SECRET"
  }
}
```

> ⚠️ Never commit `config.json` to source control.
