<img src="../static/imo_health.png" alt="IMO Health Logo" width="300"/>

---

# Precision Normalize — Value Set Matching & Cohort Builder

**Products:** IMO Precision Normalize · IMO Value Set Library

This folder contains a three-notebook pipeline that standardizes raw clinical terminology, matches it against FHIR value sets, and produces a clean, reproducible patient cohort.

---

## Notebooks

### 1. `01_IMO_Precision_Normalize.ipynb`
**Product:** IMO Precision Normalize

The first step in the pipeline. Submits raw clinical terms to the IMO Precision Normalize API to produce standardized, coded representations.

What it does:
- Installs dependencies and loads `precision_normalize` credentials from `config.json`
- Authenticates with the IMO OAuth endpoint
- Accepts a list of clinical entities (diagnoses, medications, procedures, labs)
- POSTs each entity to the Precision Normalize API
- Parses `requests[].response.items[].metadata.mappings` for ICD-10-CM, SNOMED-CT, RxNorm, CPT, and LOINC codes
- Exports `normalized_codes` — a structured list of standardized terms for use in Notebooks 2 & 3

---

### 2. `02_IMO_Value_Set_Inclusion_Criteria.ipynb`
**Product:** IMO Value Set Library

Searches the FHIR Value Set Library and downloads value sets that define which patient codes qualify for the cohort.

What it does:
- Loads `value_set` credentials and authenticates
- Searches the FHIR Value Set Library by clinical concept (e.g. "Diabetes Mellitus")
- Previews each value set's code breakdown (ICD-10-CM, SNOMED-CT counts)
- Downloads one or more value sets and stores their codes in `_inclusion_vs_codes`
- Exports inclusion criteria for use in Notebook 3

---

### 3. `03_IMO_Value_Set_Exclusion_and_Cohort.ipynb`
**Product:** IMO Value Set Library

Applies exclusion criteria and produces the final matched patient cohort.

What it does:
- Loads `value_set` credentials and authenticates
- Searches and downloads exclusion value sets (e.g. "Type 1 Diabetes") into `_exclusion_vs_codes`
- Performs local Python set matching: patient normalized codes vs. inclusion and exclusion code sets
- Identifies patients who meet inclusion criteria but are not excluded
- Exports the final cohort as a structured DataFrame

---

## Recommended Run Order

1. Run Notebook 1 to normalize raw clinical terms to standard codes
2. Run Notebook 2 to define inclusion criteria from FHIR value sets
3. Run Notebook 3 to apply exclusion criteria and export the final cohort

---

## Configuration

Copy `config.json.template` to `config.json` and fill in your credentials:

```json
{
  "precision_normalize": {
    "client_id": "YOUR_PRECISION_NORMALIZE_CLIENT_ID",
    "client_secret": "YOUR_PRECISION_NORMALIZE_CLIENT_SECRET"
  },
  "value_set": {
    "client_id": "YOUR_VALUE_SET_CLIENT_ID",
    "client_secret": "YOUR_VALUE_SET_CLIENT_SECRET",
    "vs_search_url": "YOUR_FHIR_VALUE_SET_SEARCH_URL",
    "vs_detail_url": "YOUR_FHIR_VALUE_SET_DETAIL_URL"
  }
}
```

> ⚠️ Never commit `config.json` to source control.
