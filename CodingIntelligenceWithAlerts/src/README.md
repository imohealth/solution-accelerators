# Coding Intelligence with Alerts

The IMO Coding Intelligence Solution Accelerator demonstrates how to use IMO Health's **Coding Intelligence API** to validate ICD-10-CM diagnosis codes for billing appropriateness. The app accepts CSV files with medical codes or manually inputted code lists, and flags coding issues using three rule sets from the IMO API.

---

## What It Does

### 1. Upload Codes → Validate
Upload or manually enter ICD-10-CM codes directly and the app will immediately validate them against the same rule sets.

---

## 2. Coding Intelligence Rules

Run the codes through two IMO Coding Intelligence endpoints:

| Rule | API Endpoint | What It Flags |
|------|-------------|---------------|
| **Non-Primary** | `imo-admin-coding-sets` | Codes that should not be used as a primary diagnosis |
| **Unspecified** | `imo-admin-coding-sets` | Codes that are too vague for billing — a more specific code exists |
| **Excludes 1** | `cms-excludes1` | Code pairs that CMS prohibits from being billed together |

---

## Project Structure

```
├── notebooks/
│   ├── 01_Setup_and_Authentication.ipynb     # OAuth token setup
│   ├── 02_Upload_Codes_and_Validate.ipynb    # Validate codes via imo-admin-coding-sets
│   └── 03_Excludes1_Conflict_Check.ipynb     # Check Excludes1 conflicts via cms-excludes1
└── src/
    ├── app.py               # Flask application & API routes
    ├── config.py            # API credentials and endpoint configuration
    ├── nlp_processor.py     # IMO API integration logic
    ├── requirements.txt     # Python dependencies
    ├── run.sh / run.bat     # Startup scripts
    ├── Dockerfile           # Container definition
    ├── templates/
    │   └── index.html       # Single-page frontend UI
    └── sample_data/
        └── Rules/           # Sample CSV files for code upload workflow
```

---

## Prerequisites

- Python 3.9+
- IMO Health API credentials (client ID + secret) for:
  - Entity Extraction
  - Precision Normalize
  - Coding Intelligence
- AWS credentials (for Bedrock SOAP generation and optional SSM parameter storage)

---

## Quickstart

### 1. Install dependencies
```bash
cd src
pip install -r requirements.txt
```

### 2. Configure credentials

Open `config.py` and set your IMO credentials directly:
```python
_default_imo_client_id = "your-client-id"
_default_imo_client_secret = "your-client-secret"
_default_imo_coding_intel_client_id = "your-coding-intel-client-id"
_default_imo_coding_intel_client_secret = "your-coding-intel-client-secret"
```

Or set them as environment variables:
```bash
export IMO_CLIENT_ID=your-client-id
export IMO_CLIENT_SECRET=your-client-secret
export IMO_CODING_INTEL_CLIENT_ID=your-coding-intel-client-id
export IMO_CODING_INTEL_CLIENT_SECRET=your-coding-intel-client-secret
```

Credentials can also be stored in **AWS SSM Parameter Store** — see `config.py` for parameter names.

### 3. Run the app
```bash
# macOS/Linux
./run.sh

# Windows
run.bat

# Or directly
python3 app.py
```

The app runs at **http://localhost:5001**

---

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Main UI |
| `GET` | `/ping` | Health check |
| `POST` | `/generate_soap` | Generate SOAP note from transcript |
| `POST` | `/extract_entities` | Extract diagnoses from clinical text |
| `POST` | `/normalize_entities` | Normalize entities to ICD-10-CM |
| `POST` | `/validate_billing_codes` | Check codes against `imo-admin-coding-sets` (non-primary, unspecified) |
| `POST` | `/check_excludes1` | Check code pairs against `cms-excludes1` |
| `POST` | `/refine_entities` | Trigger specificity refinement workflow |
| `POST` | `/diagnostic_workflow` | IMO diagnostic workflow lookup by lexical code |
| `POST` | `/check_refineable` | Check which codes are refineable |
| `POST` | `/get_imo_token` | Get OAuth token for client-side calls |

---

## Notebooks

The `notebooks/` folder contains Jupyter notebooks that walk through the Coding Intelligence API directly — no UI required. Useful for testing, exploration, or integration demos.

- **01_Setup_and_Authentication** — obtain an OAuth token
- **02_Upload_Codes_and_Validate** — send codes to `imo-admin-coding-sets` and parse results
- **03_Excludes1_Conflict_Check** — send code pairs to `cms-excludes1` and identify conflicts

---

## IMO Health APIs Used

| API | Base URL |
|-----|----------|
| OAuth | `https://api.imohealth.com/oauth/token` |
| Entity Extraction | `https://api.imohealth.com/entityextraction/pipelines/imo-clinical-comprehensive` |
| Precision Normalize | `https://api.imohealth.com/precision/normalize` |
| Coding Intelligence | `https://api.imohealth.com/codingintelligence/v1/rules/imo-admin-coding-sets` |
| Excludes 1 | `https://api.imohealth.com/codingintelligence/v1/rules/cms-excludes1` |
| Diagnostic Workflow | `https://api.imohealth.com/core/search/v2/product/problemIT_Professional/workflows/diagnosis` |
