<img src="./static/imo_health.png" alt="IMO Health Logo" width="300"/>

---
# RWD Cohort Identification - HL7 Workflow

A notebook-driven pipeline to parse HL7 messages, extract and normalize medical codes, and apply cohort eligibility criteria using IMO Health APIs.

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

The **HL7 Workflow** processes HL7 messages to extract medical codes and applies cohort eligibility criteria:

1. Start with HL7 messages
2. Parse and extract ICD10CM/CPT/LOINC/SNOMED codes
3. Normalize codes using IMO Health Precision API
4. Apply cohort eligibility criteria via IMO Health FHIR ValueSets

### Architecture

#### HL7 Workflow (HL7 → Codes → Cohort)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              RWD COHORT IDENTIFICATION (using-HL7)                                                            │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐  ───▶  ┌──────────────────────────┐  ───▶  ┌────────────────────────────┐  ───▶  ┌──────────────────────────┐  ───▶  ┌────────────────────────────┐  ───▶  ┌──────────────────────────┐  ───▶  ┌──────────────────────┐
│  HL7 messages        │        │  HL7 Parse & Extraction  │        │  trial_patient_dict        │        │  Code Normalization      │        │  Normalized Patient Codes  │        │  Cohort Criteria Apply   │        │  Cohort Results      │
│  uploads_hl7/hl7_data│        │  (ICD10CM/CPT/LOINC/SCT) │        │  (codes per patient)       │        │  (IMO Precision API)     │        │  (filled/corrected codes)  │        │  (IMO FHIR ValueSets)    │        │  (reports/exports)   │
└──────────────────────┘        └──────────────────────────┘        └────────────────────────────┘        └──────────────────────────┘        └────────────────────────────┘        └──────────────────────────┘        └──────────────────────┘
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
- HL7 message files

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
- HL7 messages under `uploads_hl7/hl7_data/`
- Each file contains one or more HL7 messages
- Supported message types: ADT, ORM, ORU, etc.

### Notebook Execution

Run the notebook in the `using-HL7/` folder:

**Notebook:** `SolutionAccelerator_for_RWE_Cohort_identification_withHL7.ipynb`

This single notebook handles the complete workflow:

1. **Parse HL7 Messages**
   - Input: `uploads_hl7/hl7_data/*` (HL7 message files)
   - Uses `hl7apy` library to parse HL7 v2.x messages
   - Extracts patient demographics and clinical codes

2. **Extract Medical Codes**
   - Extracts ICD10CM (diagnoses)
   - Extracts CPT (procedures)
   - Extracts LOINC (laboratory tests)
   - Extracts SNOMED CT (clinical findings)
   - Organizes codes by patient

3. **Normalize Codes (Optional)**
   - Uses IMO Health Precision Normalize API for code normalization
   - Fills incomplete codes
   - Corrects invalid codes
   - Standardizes code formats

4. **Apply Cohort Criteria**
   - Fetches ValueSets via IMO Health Precision Set FHIR API
   - Applies inclusion/exclusion criteria
   - Matches patients against trial requirements
   - Generates eligibility reports

### Path Configuration

**Important:** If running from the `using-HL7/` folder, adjust the path to HL7 data:

```python
# In the notebook, update the path:
hl7_data_path = "../uploads_hl7/hl7_data/"
```

Alternatively, start Jupyter from the project root:

```bash
cd "solution-engineering/RWE-Cohort-Identification"
jupyter lab
```

### Launch Jupyter

```bash
jupyter lab
# or
jupyter notebook
```

Select the kernel "Python (rwd-cohort)" and Run All Cells in the notebook.

## Features and Settings

### HL7 Parsing

- Library: `hl7apy` for parsing HL7 v2.x messages
- Supported segments: PID, DG1, PR1, OBR, OBX, etc.
- Configurable message encoding and validation

### Code Extraction

Extracted code types and typical HL7 segments:
- **ICD10CM**: DG1 segment (diagnosis)
- **CPT**: PR1 segment (procedures)
- **LOINC**: OBX segment (observations/labs)
- **SNOMED CT**: Various segments depending on message type

### Code Normalization (IMO Health Precision Normalize API)

Optional normalization features:
- Fill incomplete codes (e.g., "E11" → "E11.9")
- Correct invalid codes
- Standardize code formats
- Map to preferred terms

Adjustable parameters:

```python
use_normalization = True  # Enable/disable IMO Health Precision Normalize API calls
request_delay = 0.5       # Seconds between API calls to avoid rate limiting
```

### Cohort Matching

- Uses IMO Health FHIR ValueSet API to fetch trial criteria
- Supports multiple code systems (ICD10CM, CPT, LOINC, SNOMED)
- Generates patient eligibility reports
- Exports results for analysis

## Troubleshooting

### Common Issues

1. **Authentication Error (IMO Health Auth0)**
  - Verify `domain`, `client_id`, `client_secret`, `audience` in `config.json`
  - Ensure credentials are for the correct environment

2. **HL7 Parsing Errors**
  - Check HL7 message format and encoding
  - Verify message follows HL7 v2.x standard
  - Use HL7 validation tools to check message structure
  - Check for special characters or encoding issues

3. **Rate Limiting (HTTP 429)**
  - Notebooks include pacing and retry logic
  - Adjust `request_delay` parameter
  - Process smaller batches of patients

4. **Missing HL7 Files**
  - Verify files exist in `uploads_hl7/hl7_data/`
  - Check file permissions
  - Ensure files are not empty

5. **Code Extraction Issues**
  - Not all HL7 messages contain clinical codes
  - Check that the message type is supported
  - Verify segment structure matches expectations

6. **Memory Issues with Large Files**
  - Process HL7 files in batches
  - Increase available memory
  - Consider splitting large HL7 files

## Output Format

Directory structure and key files:

```
Output/
├── trial_patient_dict.json                  # Extracted codes by patient
├── normalized_codes.csv                     # Normalized medical codes
├── cohort_matching_results.csv              # Final cohort eligibility results
└── patient_reports/                         # Individual patient reports
    ├── patient_001_report.json
    ├── patient_002_report.json
    └── ...
```

### Output File Descriptions

- **trial_patient_dict.json**: Dictionary of all extracted codes organized by patient ID
- **normalized_codes.csv**: Medical codes after IMO Health Precision normalization
- **cohort_matching_results.csv**: Patient eligibility results with inclusion/exclusion criteria matching
- **patient_reports/**: Detailed reports for each patient including matched criteria

### Sample Output Structure

```json
{
  "patient_001": {
    "demographics": {
      "patient_id": "patient_001",
      "name": "John Doe",
      "dob": "1975-05-15"
    },
    "diagnoses": ["E11.9", "I10", "Z79.4"],
    "procedures": ["99213", "80053"],
    "labs": ["2339-0", "2345-7"],
    "cohort_eligible": true,
    "matched_criteria": ["diabetes_type_2", "hypertension"]
  }
}
```

## Support

For questions or issues, contact:
- IMO Health API Support: support@imohealth.com
