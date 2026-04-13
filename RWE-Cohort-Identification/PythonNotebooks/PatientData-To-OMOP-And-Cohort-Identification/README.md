<img src="./static/imo_health.png" alt="IMO Health Logo" width="300"/>

---
# RWD Cohort Identification - OMOP Workflow

A notebook-driven pipeline to extract structured patient data from clinical notes, convert results to OMOP CDM, and apply cohort eligibility criteria using IMO Health APIs.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Features and Settings](#features-and-settings)
- [Troubleshooting](#troubleshooting)
- [Output Format](#output-format)
- [Support](#support)

## Overview

The **OMOP Workflow** transforms de-identified clinical notes into OMOP CDM format and applies cohort eligibility criteria:

1. Start with de-identified clinical notes in CSV
2. Extract entities via IMO Health NLP API → Excel
3. Convert to OMOP CDM tables
4. Apply cohort eligibility criteria via IMO Health Precision Set FHIR API

### Architecture

#### OMOP Workflow (Notes → OMOP → Cohort)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              RWD COHORT IDENTIFICATION (using-OMOP)                                                            │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐  ───▶  ┌──────────────────────┐  ───▶  ┌──────────────────────┐  ───▶  ┌──────────────────────────┐  ───▶  ┌──────────────────────┐  ───▶  ┌──────────────────────────┐  ───▶  ┌──────────────────────┐
│  Notes (CSV input)   │        │   IMO NLP API        │        │  patient_output.xlsx │        │   OMOP Conversion        │        │  OMOP CSV Tables     │        │  Cohort Criteria Apply   │        │  Cohort Results      │
│  upload_ihm/*.csv    │        │  Entity Extraction   │        │  (structured results)│        │  (vocabularies/*.csv)    │        │  Output/OMOP_CSV/*   │        │  (IMO FHIR ValueSets)    │        │  (reports/exports)   │
└──────────────────────┘        └──────────────────────┘        └──────────────────────┘        └──────────────────────────┘        └──────────────────────┘        └──────────────────────────┘        └──────────────────────┘
```

```
Legend:
┌────┐ Step    │  Data ▶▶▶ Flow
└────┘ Object
```

## Prerequisites

- Python 3.9 or higher
- IMO Health API credentials (Auth0 client credentials)
- Jupyter Notebook/Lab or VS Code + Jupyter extension
- **OMOP vocabularies** (required for conversion): 
  - Download from OHDSI Athena: https://athena.ohdsi.org/vocabulary/list
  - Required files: `vocabularies/CONCEPT.csv`, `vocabularies/CONCEPT_RELATIONSHIP.csv`

## Installation

1. Navigate to the RWE-Cohort-Identification folder:
  ```bash
  cd "solution-engineering/RWE-Cohort-Identification"
  ```

2. Create and activate a virtual environment.

  Windows (PowerShell):
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install --upgrade pip
  ```

  macOS/Linux (bash):
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  ```

3. Install the required packages (from requirements.txt):

  ```bash
  pip install -r requirements.txt
  ```

4. (Optional) Register the kernel for Jupyter/VS Code:

  ```bash
  python -m ipykernel install --user --name rwd-cohort-notebooks --display-name "Python (rwd-cohort)"
  ```

## Configuration

Configure IMO Health API access in `config.json` (in the parent RWE-Cohort-Identification folder):

```json
{
  "auth0": {
   "domain": "auth.imohealth.com",
   "client_id": "YOUR_IMO_CLIENT_ID",
   "client_secret": "YOUR_IMO_CLIENT_SECRET",
   "audience": "https://api.imohealth.com"
  },
  "api": { "base_url": "https://api.imohealth.com" }
}
```

## Usage

### Input Requirements

Prerequisites:
- Notes CSVs in `upload_ihm/` with columns: `hospitalGuid`, `encounterGuid`, `patientGuid`, `notesDEID`
- OMOP vocabularies in `vocabularies/`: `CONCEPT.csv`, `CONCEPT_RELATIONSHIP.csv` (tab-delimited from OHDSI Athena)

### Notebook Execution Order

Run the notebooks in the `using-OMOP/` folder in this order:

#### 1. Extract Entities from Clinical Notes

**Notebook:** `01_SolutionAccelerator_RWE_Extraction_From_Notes_To_Patient_Data.ipynb`

- **Input:** `upload_ihm/*.csv` (clinical notes)
- **Process:** Calls IMO Health NLP API to extract medical entities (problems, procedures, medications, labs)
- **Output:** `Output/patient_output.xlsx` (structured patient data)

#### 2. Convert to OMOP CDM Format

**Notebook:** `02_SolutionAccelerator_RWE_Patient_Data_to_OMOP_Converter.ipynb`

- **Input:** 
  - `Output/patient_output.xlsx` (from step 1)
  - `vocabularies/CONCEPT.csv` and `vocabularies/CONCEPT_RELATIONSHIP.csv`
- **Process:** Maps ICD10CM/RXNORM/LOINC/CPT to OMOP standard concepts
- **Output:** `Output/OMOP_CSV/*.csv` (OMOP CDM tables)

#### 3. Apply Cohort Eligibility Criteria

**Notebook:** `03_SolutionAccelerator_RWE_Applying_Cohort_Criteria.ipynb`

- **Input:** `Output/OMOP_CSV/*.csv` (from step 2)
- **Process:** 
  - Fetch ValueSets via IMO Health Precision Sets FHIR API
  - Apply inclusion/exclusion criteria
  - Match patients against trial requirements
- **Output:** Cohort results and reports

### Launch Jupyter

```bash
jupyter lab
# or
jupyter notebook
```

Select the kernel "Python (rwd-cohort)" and Run All Cells in each notebook in the order above.

## Features and Settings

### NLP Extraction (Step 1)

- Endpoint: IMO Health Clinical Comprehensive NLP (`/entityextraction/pipelines/imo-clinical-comprehensive?version=3.0`)
- Adjustable parameters inside the notebook:

```python
domain_filter = ["problem", "procedure", "medication", "lab"]
score_threshold = 0.0
request_delay = 0.5  # seconds between API calls to avoid rate limiting
```

### OMOP Conversion (Step 2)

- Requires `vocabularies/CONCEPT.csv` and `vocabularies/CONCEPT_RELATIONSHIP.csv`
- Maps source codes to OMOP standard concepts
- Creates standard OMOP CDM tables:
  - PERSON
  - VISIT_OCCURRENCE
  - CONDITION_OCCURRENCE
  - DRUG_EXPOSURE
  - MEASUREMENT
  - PROCEDURE_OCCURRENCE

### Cohort Matching (Step 3)

- Uses IMO Health Precision Set FHIR  API to fetch trial criteria
- Supports inclusion/exclusion criteria
- Generates patient eligibility reports

## Troubleshooting

### Common Issues

1. **Authentication Error (IMO Health Auth0)**
  - Verify `domain`, `client_id`, `client_secret`, `audience` in `config.json`
  - Ensure credentials are for the correct environment

2. **Rate Limiting (HTTP 429)**
  - Notebooks include pacing and retry examples
  - Adjust `request_delay` parameter in the extraction notebook
  - Re-run after a short wait

3. **Missing CSV Columns**
  - Ensure notes CSVs include: `hospitalGuid`, `encounterGuid`, `patientGuid`, `notesDEID`
  - Check CSV encoding (UTF-8 recommended)

4. **OMOP Vocabulary Files Not Found**
  - Download from OHDSI Athena: https://athena.ohdsi.org/vocabulary/list
  - Place files in `vocabularies/` folder
  - Ensure files are tab-delimited

5. **Excel Write/Read Issues**
  - Confirm `openpyxl` and `xlsxwriter` are installed: `pip install openpyxl xlsxwriter`
  - Verify sufficient disk space for output files

6. **Memory Issues with Large Datasets**
  - Process notes in batches
  - Increase available memory or use a machine with more RAM

## Output Format

Directory structure and key files:

```
Output/
├── patient_output.xlsx                      # Structured extraction results
├── cohort_matching_results.csv              # Final cohort eligibility results
└── OMOP_CSV/                                # OMOP CDM format tables
   ├── PERSON.csv
   ├── VISIT_OCCURRENCE.csv
   ├── CONDITION_OCCURRENCE.csv
   ├── DRUG_EXPOSURE.csv
   ├── MEASUREMENT.csv
   └── PROCEDURE_OCCURRENCE.csv
```

### Output File Descriptions

- **patient_output.xlsx**: Structured patient data with extracted entities from clinical notes
- **cohort_matching_results.csv**: Patient eligibility results with inclusion/exclusion criteria matching
- **OMOP_CSV/*.csv**: Standard OMOP CDM tables ready for analytics and research

## Support

For questions or issues, contact:
- IMO Health API Support: support@imohealth.com
