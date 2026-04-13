<img src="./PythonNotebooks/static/imo_health.png" alt="IMO Health Logo" width="300"/>

---

# Ambient AI Solution - PythonNotebook

This repository contains Jupyter notebooks and supporting files for the Ambient AI Solution Accelerator. It demonstrates a complete medical AI pipeline for transforming clinical transcripts into structured, coded documentation using AWS and IMO Health APIs.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Folder Structure](#folder-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Sample Data](#sample-data)
- [Output Files](#output-files)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Resources](#resources)
- [Contributing](#contributing)
- [Support](#support)


## Overview
The Ambient AI Solution transforms medical transcripts from ambient listening into structured, coded clinical documentation through a 4-step workflow:
1. **Transcript to SOAP Generation**: Convert free-text medical transcripts into structured SOAP notes
2. **Entity Extraction with Context**: Identify and extract medical entities with contextual information
3. **Normalize with Enrichment**: Map entities to standard medical terminologies
4. **Diagnostic Specificity Workflow**: Refine entities to achieve billing-ready diagnostic codes

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  📄 INPUT: Medical Transcript                                   │
│  Source: sample_data/*.txt                                      │
│  Format: Free-text clinical conversation or dictation          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Transcript to SOAP Generation                         │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Notebook: 01_transcript_to_soap_generation.ipynb              │
│  Service: Amazon Bedrock (Nova Pro Model)                      │
│  Process: Uses LLM to transform unstructured transcript into   │
│           structured SOAP note with Subjective, Objective,     │
│           Assessment, and Plan sections                        │
│  Input: Raw medical transcript text                            │
│  Output: Structured JSON with S/O/A/P sections                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  📋 ARTIFACT: SOAP Note                                         │
│  File: soap_note_output.json                                   │
│  Contains: Structured clinical note with 4 sections            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Entity Extraction with Context                        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Notebook: 02_entity_extraction_with_context.ipynb             │
│  Service: IMO Health API (Lexical Search)                      │
│  Process: Identifies and extracts medical entities (problems,  │
│           medications, procedures) with contextual attributes  │
│           (status, severity, laterality)                       │
│  Input: SOAP note JSON                                         │
│  Output: List of medical entities with context metadata        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  🔍 ARTIFACT: Extracted Entities                                │
│  File: extracted_entities_output.json                          │
│  Contains: Medical terms with context (negation, temporality)  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Normalize with Enrichment                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Notebook: 03_normalize_with_enrichment.ipynb                  │
│  Service: IMO Health API (Problem Normalization)               │
│  Process: Maps extracted entities to standard medical          │
│           terminologies (SNOMED CT, ICD-10) and enriches with  │
│           additional clinical details and synonyms             │
│  Input: Extracted entities JSON                                │
│  Output: Normalized entities with standard codes               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  📊 ARTIFACT: Normalized Entities                               │
│  File: normalized_entities_output.json                         │
│  Contains: Standard codes (SNOMED, ICD-10) and mappings        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Diagnostic Specificity Workflow                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Notebook: 04_diagnostic_specificity_workflow.ipynb            │
│  Service: IMO Health API (Specificity Check & Refinement)      │
│  Process: Analyzes diagnostic codes for billing specificity,   │
│           identifies vague codes, and refines them to more     │
│           specific ICD-10 codes suitable for reimbursement     │
│  Input: Normalized entities JSON                               │
│  Output: Billing-ready ICD-10 codes with specificity details   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ✅ FINAL OUTPUT: Refined Entities with ICD-10 Codes           │
│  File: refined_entities_output.json                            │
│  Contains: Specific ICD-10 codes ready for clinical billing    │
└─────────────────────────────────────────────────────────────────┘
```

## Features
- End-to-end medical NLP pipeline
- Integration with Amazon Bedrock and IMO Health APIs
- Entity extraction, normalization, and diagnostic refinement
- Educational notebooks with code, explanations, and sample data

## Folder Structure
```
PythonNotebook/
  config.py                # API credentials and configuration
  notebooks/               # Jupyter notebooks for each workflow step
    01_transcript_to_soap_generation.ipynb
    02_entity_extraction_with_context.ipynb
    03_normalize_with_enrichment.ipynb
    04_diagnostic_specificity_workflow.ipynb
  sample_data/             # Example medical transcripts
    sample_transcript.txt
    inpatient-transcript3.txt
    outpatient-transcript1.txt
    outpatient-transcript2.txt
```

## Prerequisites
Before starting, ensure you have the following:

### Required Software
- **Python 3.8+**: Download from [python.org](https://www.python.org/downloads/)
- **pip**: Python package installer (included with Python 3.4+)
- **Git**: Version control system for cloning the repository
- **Jupyter Notebook**: Will be installed via pip in the installation steps

### Required Accounts & Access
- **AWS Account**: 
  - Active AWS account
  - IAM user with permissions for Amazon Bedrock
  
- **IMO Health API Access**:
  - Active IMO Health account
  - OAuth2 credentials (Client ID and Client Secret)
  - API access to the following endpoints:
    - Lexical Search API
    - Problem Normalization API
    - Specificity Check API

### System Requirements
- **Operating System**: Windows, macOS, or Linux
- **RAM**: Minimum 4GB (8GB recommended)
- **Disk Space**: At least 500MB free space
- **Internet Connection**: Required for API calls to AWS Bedrock and IMO Health

### Knowledge Prerequisites
- Basic understanding of Python programming
- Familiarity with Jupyter Notebooks
- Basic knowledge of medical terminology (helpful but not required)
- Understanding of REST APIs and JSON format

## Installation
1. **Clone the repository**
   ```bash
   git clone https://github.com/imohealth/solution-engineering.git
   cd Ambient-AI-Solution/PythonNotebook
   ```
2. **Create and activate a virtual environment (recommended)**
   ```bash
   # Windows:
   python -m venv venv
   venv\Scripts\activate
   
   # macOS/Linux:
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   # Windows:
   pip install boto3>=1.34.0 requests>=2.31.0 jupyter
   
   # macOS/Linux:
   pip3 install boto3>=1.34.0 requests>=2.31.0 jupyter
   ```
   
   **Required packages:**
   - `boto3` (>=1.34.0) - AWS SDK for Python to interact with Amazon Bedrock
   - `requests` (>=2.31.0) - HTTP library for IMO Health API calls
   - `jupyter` - Jupyter Notebook environment
   
   > **Note for macOS users**: If you encounter SSL certificate errors, you may need to run: 
   > `/Applications/Python\ 3.x/Install\ Certificates.command` (replace 3.x with your Python version)
   
4. **Configure credentials**   
   
   ### a. IMO Health API Configuration
   Edit the `config.py` file in the PythonNotebook directory:
   
   ```python 
   
   
   imo_entity_extraction_client_id = "YOUR_IMO_ENTITY_EXTRACTION_API_CLIENT_ID"
   imo_entity_extraction_client_secret = "YOUR_IMO_ENTITY_EXTRACTION_API_CLIENT_SECRET"
   imo_normalize_enrichment_api_client_id = "YOUR_IMO_ENRICHMENT_API_CLIENT_ID"
   imo_normalize_enrichment_api_client_secret = "YOUR_IMO_ENRICHMENT_API_CLIENT_SECRET"
   imo_diagnostic_workflow_client_id = "YOUR_IMO_DIAGNOSTIC_WORKFLOW_API_CLIENT_ID"	
   imo_diagnostic_workflow_client_secret = "YOUR_IMO_DIAGNOSTIC_WORKFLOW_API_CLIENT_SECRET"
      
   ```
   
   > ⚠️ **Security Warning**: Never commit `config.py` with actual credentials to version control. 
   > Add `config.py` to `.gitignore` or use environment variables/AWS SSM for production.
   
5. **Start Jupyter**
   ```bash
   jupyter notebook notebooks/
   ```

## Usage
### Running the Complete Workflow
1. Open and run all cells in `01_transcript_to_soap_generation.ipynb` (input: sample transcript)
2. Continue with `02_entity_extraction_with_context.ipynb` (input: SOAP note from step 1)
3. Proceed to `03_normalize_with_enrichment.ipynb` (input: entities from step 2)
4. Finish with `04_diagnostic_specificity_workflow.ipynb` (input: normalized entities from step 3)

### Running Individual Steps
Each notebook can be run independently if the required input file exists:
- Notebook 1: Needs `sample_data/sample_transcript.txt`
- Notebook 2: Needs `soap_note_output.json`
- Notebook 3: Needs `extracted_entities_output.json`
- Notebook 4: Needs `normalized_entities_output.json`

## Sample Data
Sample medical transcripts are provided in `sample_data/`. You can use your own transcripts by replacing these files.

## Output Files
| Notebook | Output File                  | Contents                                 |
|----------|------------------------------|------------------------------------------|
| 1        | soap_note_output.json        | Structured SOAP note (S/O/A/P sections)  |
| 2        | extracted_entities_output.json| Medical entities with context            |
| 3        | normalized_entities_output.json| Normalized entities with standard codes  |
| 4        | refined_entities_output.json | Refined entities with ICD-10 codes       |

## Troubleshooting
- **AWS Bedrock Access Denied**: Ensure credentials have Bedrock permissions and Nova Pro is enabled
- **IMO Health API Unauthorized**: Check OAuth credentials in `config.py` and API access
- **Missing Dependencies**: Run `pip install --upgrade boto3 requests jupyter`

## Best Practices
- Never commit `config.py` with API keys to version control
- Use de-identified sample data only
- Review error messages in each cell
- Be mindful of API rate limits
- Follow HIPAA guidelines for PHI


## Resources
- [IMO Health Documentation](https://developer.imohealth.com/)
- [Amazon Bedrock Guide](https://docs.aws.amazon.com/bedrock/)
- [ICD-10-CM Codes](https://www.cms.gov/medicare/coding-billing/icd-10-codes)
- [SNOMED CT](https://www.snomed.org/)

## Contributing
Improvements welcome! Please:
- Maintain educational focus
- Include comprehensive documentation
- Test with sample data
- Follow existing code style

## Support

For questions or issues, contact:
- IMO Health API Support: support@imohealth.com



