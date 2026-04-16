<img src="../static/imo_health.png" alt="IMO Health Logo" width="300"/>

---

# Search and Capture

**Products:** IMO Core Search · IMO Problem List Management · IMO Coding Intelligence

This folder contains a three-notebook workflow that covers the full clinical coding lifecycle — from interactive term search and specialty grouping through duplicate detection and ICD-10-CM coding rule validation.

---

## Notebooks

### 1. `01_IMO_Core_Search_Setup.ipynb`
**Product:** IMO Core Search

The setup and authentication notebook. Establishes credentials and verifies connectivity to all three product APIs before running the workflow.

What it does:
- Installs dependencies and loads credentials for all three products (`core_search`, `problem_list`, `coding_intelligence`) from `config.json`
- Authenticates with the IMO OAuth endpoint and obtains bearer tokens for each product
- Probes all downstream API endpoints to confirm they are reachable and responding
- Sets up shared helper functions (`cs_headers`, `pl_headers`, `ci_headers`) ready for Notebooks 2 & 3

---

### 2. `02_IMO_Core_Search_and_Problem_List_Categorize.ipynb`
**Products:** IMO Core Search · IMO Problem List Management

Demonstrates clinical term search and specialty-based problem list categorization.

What it does:
- POSTs search terms to the IMO Core Search API across multiple clinical domains (diagnoses, procedures, medications, labs)
- Parses `SearchTermResponse.items[]` for IMO lexical codes, ICD-10-CM, SNOMED-CT, and CPT codes
- Calls the suggest endpoint for type-ahead / alternative term suggestions
- Builds a `captured_problems` list from search results
- POSTs the problem list to the IMO Categorize endpoint
- Displays specialty groupings (`categories[]`) and a problem-count summary

---

### 3. `03_IMO_Problem_List_Clean_and_Coding_Intelligence.ipynb`
**Products:** IMO Problem List Management · IMO Coding Intelligence

Cleans the problem list and validates ICD-10-CM codes against CMS coding rules.

What it does:
- Accepts `captured_problems` from Notebook 2 (same kernel session) or uses a built-in sample
- POSTs to the IMO Clean endpoint and displays all four response groups (`acute`, `lapsed`, `duplicates`, `related`)
- Extracts ICD-10-CM codes from the cleaned problem list
- POSTs codes to the IMO Coding Intelligence `imo-admin-coding-sets` endpoint to flag non-primary and unspecified codes
- POSTs codes to the `cms-excludes1` endpoint to detect CMS Excludes 1 conflicts
- Displays a consolidated validation report with flags per code

---

## Recommended Run Order

1. Run Notebook 1 to verify credentials and API connectivity
2. Run Notebook 2 to search for clinical terms and categorize the resulting problem list
3. Run Notebook 3 to clean the problem list and validate codes against CMS coding rules

---

## Configuration

Copy `config.json.template` to `config.json` and fill in your credentials:

```json
{
  "core_search": {
    "client_id": "YOUR_CORE_SEARCH_CLIENT_ID",
    "client_secret": "YOUR_CORE_SEARCH_CLIENT_SECRET"
  },
  "problem_list": {
    "client_id": "YOUR_PROBLEM_LIST_CLIENT_ID",
    "client_secret": "YOUR_PROBLEM_LIST_CLIENT_SECRET"
  },
  "coding_intelligence": {
    "client_id": "YOUR_CODING_INTELLIGENCE_CLIENT_ID",
    "client_secret": "YOUR_CODING_INTELLIGENCE_CLIENT_SECRET"
  }
}
```

> ⚠️ Never commit `config.json` to source control.
