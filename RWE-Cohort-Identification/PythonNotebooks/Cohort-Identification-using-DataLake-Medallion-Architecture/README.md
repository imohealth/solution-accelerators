<img src="./static/imo_health.png" alt="IMO Health Logo" width="300"/>

---
# RWD Cohort Identification - Data Lake Workflow (Medallion Architecture)

A notebook-driven pipeline implementing a medallion architecture (Bronze/Silver/Gold) for governed data processing, normalization, and cohort identification at scale.

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

The **Data Lake Workflow** implements a medallion architecture for scalable data processing:

1. **Bronze Zone**: Raw data ingestion and historical archiving
2. **Silver Zone**: Data normalization and enrichment using IMO Health APIs
3. **Gold Zone**: Curated, cohort-filtered data ready for analytics

This approach enables:
- Governed data layers with clear quality progression
- Standardized medical terminology using IMO Health Precision API
- Cohort identification at scale
- Production-ready analytics datasets

### Architecture

#### Data Lake Workflow (Medallion Pipeline)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MEDALLION DATA LAKE ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
    │              │         │              │         │              │
    │   🥉 BRONZE  │────────▶│  🥈 SILVER   │────────▶│   🥇 GOLD    │
    │     ZONE     │         │     ZONE     │         │     ZONE     │
    │              │         │              │         │              │
    └──────────────┘         └──────────────┘         └──────────────┘
         │                          │                        │
         │                          │                        │
    Raw Patient              Normalized Data          Cohort-Filtered
    Data Ingestion           (IMO Health Precision     Patient Records
    (CSV files)              Normalize API)           (Final Analytics)
         │                          │                        │
         │                          │                        │
    • Unprocessed          • Standardized codes       • Business-ready
    • As-is storage        • LOINC, ICD10CM           • Criteria-matched
    • Historical           • RXNORM, CPT              • Decision support
      archive              • Quality improved         • Reporting
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
- AWS account with S3 access (for cloud storage)
- boto3 configured for AWS access (optional for local development)

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

### IMO Health API Configuration

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

### AWS S3 Configuration (Optional)

For cloud storage, configure AWS credentials:

```bash
# Set environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"

# Or configure using AWS CLI
aws configure
```

For local development, the notebook can use local filesystem paths instead of S3.

## Usage

### Input Requirements

Prerequisites:
- Patient data CSV file: `DQA_Input.csv` in the `using-DataLake-Architecture/` folder
- CSV should contain patient demographics and clinical codes
- Required columns depend on your data model (configurable in the notebook)

### Notebook Execution

Run the notebook in the `using-DataLake-Architecture/` folder:

**Notebook:** `Medallion_DataLake_Patient_Pipeline.ipynb`

This notebook implements the complete medallion architecture pipeline:

#### 1. Bronze Zone - Raw Data Ingestion

**Purpose:** Ingest raw data as-is for historical archiving

- **Input:** `DQA_Input.csv` (local file or S3)
- **Process:**
  - Load raw patient data without transformation
  - Store in Bronze zone (local folder or S3 bucket)
  - Preserve original data for audit and reprocessing
- **Output:** `bronze/patient_data.csv`

**Key Features:**
- No data validation or transformation
- Complete data lineage tracking
- Append-only storage for historical reference

#### 2. Silver Zone - Normalization and Enrichment

**Purpose:** Clean, standardize, and enrich data using IMO APIs

- **Input:** `bronze/patient_data.csv`
- **Process:**
  - Data quality validation and cleansing
  - Medical code normalization via IMO Precision API
  - Code system enrichment (LOINC, ICD10CM, RXNORM, CPT)
  - Fill incomplete codes
  - Correct invalid codes
  - Add standard descriptions and metadata
- **Output:** `silver/normalized_patient_data.csv`

**Key Features:**
- Schema enforcement and validation
- Duplicate detection and handling
- IMO Health Precision Normalize API integration for medical terminology
- Data quality metrics and reporting

#### 3. Gold Zone - Cohort Curation

**Purpose:** Create business-ready, cohort-filtered datasets

- **Input:** 
  - `silver/normalized_patient_data.csv`
  - IMO Health FHIR ValueSets (cohort criteria)
- **Process:**
  - Fetch cohort criteria via IMO Health Precision Sets FHIR API
  - Apply inclusion/exclusion rules
  - Filter patients meeting eligibility requirements
  - Aggregate and summarize for analytics
- **Output:** `gold/cohort_patient_data.csv`

**Key Features:**
- Business rules application
- Cohort segmentation
- Analytics-ready format
- Performance optimization for queries

### Launch Jupyter

```bash
jupyter lab
# or
jupyter notebook
```

Select the kernel "Python (rwd-cohort)" and Run All Cells in the notebook.

## Features and Settings

### Bronze Zone Configuration

```python
# Storage configuration
USE_S3 = False  # Set to True for S3 storage, False for local
S3_BUCKET = "my-datalake-bucket"
BRONZE_PREFIX = "bronze/"
LOCAL_BRONZE_PATH = "./bronze/"

# Ingestion settings
APPEND_MODE = True  # Append new data vs. overwrite
INCLUDE_TIMESTAMP = True  # Add ingestion timestamp
```

### Silver Zone Configuration

```python
# Data quality settings
DROP_DUPLICATES = True
VALIDATE_SCHEMA = True
FILL_MISSING_VALUES = False

# IMO Health Precision Normalize API settings
USE_NORMALIZATION = True
CODE_SYSTEMS = ["ICD10CM", "LOINC", "RXNORM", "CPT"]
request_delay = 0.5  # Rate limiting

# Quality thresholds
MIN_DATA_QUALITY_SCORE = 0.7
REQUIRED_FIELDS = ["patient_id", "encounter_id"]
```

### Gold Zone Configuration

```python
# Cohort criteria
COHORT_NAME = "diabetes_study"
INCLUSION_CRITERIA = ["diabetes_type_2", "age_18_65"]
EXCLUSION_CRITERIA = ["pregnancy", "liver_disease"]

# Output format
EXPORT_FORMAT = "csv"  # csv, parquet, or json
INCLUDE_METADATA = True
```

## Troubleshooting

### Common Issues

1. **Authentication Error (IMO Health Auth0)**
  - Verify `domain`, `client_id`, `client_secret`, `audience` in `config.json`
  - Ensure credentials are for the correct environment

2. **AWS S3 Access Errors**
  - Verify AWS credentials are configured
  - Check S3 bucket permissions
  - Ensure bucket exists in the specified region
  - For local development, set `USE_S3 = False`

3. **Rate Limiting (HTTP 429)**
  - Adjust `request_delay` parameter for IMO Health API calls
  - Process data in smaller batches
  - Implement exponential backoff

4. **Data Quality Issues**
  - Review Bronze zone data for source data problems
  - Check required field mappings
  - Validate CSV encoding (UTF-8 recommended)

5. **Memory Issues with Large Datasets**
  - Process data in chunks using pandas
  - Increase available memory
  - Consider using Dask for larger-than-memory datasets
  - Optimize data types (e.g., use categories for repeated strings)

6. **Missing Input Files**
  - Verify `DQA_Input.csv` exists in `using-DataLake-Architecture/`
  - Check file permissions
  - Ensure CSV is properly formatted

7. **Zone Directory Errors**
  - Ensure Bronze/Silver/Gold directories exist or can be created
  - Check write permissions for output directories
  - For S3, verify bucket and prefix configuration

## Output Format

### Local Filesystem Structure

```
using-DataLake-Architecture/
├── DQA_Input.csv                           # Input data
├── bronze/                                 # Bronze Zone - Raw Data
│   ├── patient_data.csv
│   └── metadata/
│       ├── ingestion_log.json
│       └── data_lineage.json
├── silver/                                 # Silver Zone - Normalized Data
│   ├── normalized_patient_data.csv
│   └── quality_reports/
│       ├── validation_report.json
│       └── normalization_stats.json
├── gold/                                   # Gold Zone - Curated Data
│   ├── cohort_patient_data.csv
│   ├── cohort_summary.json
│   └── analytics/
│       ├── cohort_demographics.csv
│       └── eligibility_breakdown.json
└── logs/                                   # Pipeline Logs
    ├── pipeline_run_log.json
    └── error_log.txt
```

### S3 Storage Structure

```
s3://my-datalake-bucket/
├── bronze/
│   └── patient_data/
│       └── 2026-01-20/patient_data.csv
├── silver/
│   └── normalized_patient_data/
│       └── 2026-01-20/normalized_patient_data.csv
└── gold/
    └── cohort_patient_data/
        └── 2026-01-20/cohort_patient_data.csv
```

### Output File Descriptions

#### Bronze Zone
- **patient_data.csv**: Raw patient data exactly as ingested
- **ingestion_log.json**: Metadata about ingestion timestamp, source, and record count

#### Silver Zone
- **normalized_patient_data.csv**: Cleaned and normalized patient data with standardized medical codes
- **validation_report.json**: Data quality metrics and validation results
- **normalization_stats.json**: Statistics on code normalization (corrections, fills, enrichments)

#### Gold Zone
- **cohort_patient_data.csv**: Final curated dataset of patients meeting cohort criteria
- **cohort_summary.json**: Summary statistics of the cohort
- **eligibility_breakdown.json**: Detailed breakdown of inclusion/exclusion criteria matching

### Data Quality Metrics

Each zone includes quality metrics:

```json
{
  "zone": "silver",
  "timestamp": "2026-01-20T10:30:00Z",
  "record_count": 10000,
  "quality_score": 0.95,
  "completeness": 0.98,
  "accuracy": 0.94,
  "consistency": 0.96,
  "issues": {
    "duplicates_removed": 45,
    "invalid_codes_corrected": 123,
    "missing_values_filled": 67
  }
}
```

## Best Practices

### Data Lake Architecture

1. **Never modify Bronze data** - It's your source of truth
2. **Version your transformations** - Track changes to Silver/Gold logic
3. **Partition by date** - Enable efficient time-based queries
4. **Document data lineage** - Track data flow through zones
5. **Monitor data quality** - Set up automated quality checks

### Performance Optimization

1. Use columnar formats (Parquet) for large datasets
2. Partition data by frequently queried dimensions
3. Cache Silver zone results for repeated Gold zone processing
4. Batch API calls to IMO Health services
5. Use appropriate data types to minimize memory usage

### Security and Compliance

1. Encrypt data at rest and in transit
2. Implement access controls for each zone
3. Maintain audit logs of all data access
4. Ensure PHI/PII is properly de-identified
5. Follow HIPAA compliance requirements

## Support

For questions or issues, contact:
- IMO Health API Support: support@imohealth.com
