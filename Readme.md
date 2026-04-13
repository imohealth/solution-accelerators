<p align="center">
  <img src="./static/imo_health.png" alt="IMO Health Logo" width="400"/>
</p>

## Overview

Welcome to the **IMO Health Solution Accelerators** repository. This repository serves as a comprehensive collection of blueprints and solution accelerators that demonstrate how to integrate with IMO Health's powerful capabilities and APIs.

IMO Health provides industry-leading clinical terminology, analytics, and AI-powered solutions that help healthcare organizations improve clinical documentation, enhance data quality, and drive better patient outcomes. This repository contains practical, real-world implementations and reference architectures to help you quickly integrate IMO Health's capabilities into your healthcare applications and workflows.

## Solutions Inventory

### 1. Ambient AI Solution
Advanced AI-powered solutions for clinical documentation and workflow automation.

**Key Capabilities:**
- Entity extraction with clinical context using IMO Health NLP Api
- Data normalization and enrichment using IMO Health Precision Normalization API
- Diagnostic specificity workflows using IMO Health Modifier API

📖 [View Ambient AI Solution Documentation](Ambient%20AI%20Solution/Readme.md)

---

### 2. RWE Cohort Identification
Real-World Evidence (RWE) solutions for patient cohort identification and OMOP data transformation.

**Key Capabilities:**
- Data Normalization of structured and unstructured data using IMO Health Precision Normalize API
- Patient Cohorting using IMO Health Precision Set API



**Solutions:**
- [Cohort Identification using DataLake Medallion Architecture](RWE-Cohort-Identification/PythonNotebooks/Cohort-Identification-using-DataLake-Medallion-Architecture/README.md) - Medallion architecture data lake implementation
- [Cohort Identification using HL7 Data](RWE-Cohort-Identification/PythonNotebooks/Cohort-Identification-using-HL7-Data/README.md) - HL7 data processing and cohort identification
- [Patient Data Extraction from Notes](RWE-Cohort-Identification/PythonNotebooks/PatientData-To-OMOP-And-Cohort-Identification/README.md) - Extract structured patient data from clinical notes
- [Patient Data to OMOP Conversion and Cohort Criteria](RWE-Cohort-Identification/PythonNotebooks/PatientData-To-OMOP-And-Cohort-Identification/README.md) - OMOP CDM data conversion and cohort criteria application

---

## Getting Started

Each solution includes:
- 📓 Jupyter notebooks with step-by-step implementations
- 📋 Sample data and configuration files
- 📝 Detailed README documentation
- 🔧 Requirements and setup instructions

## Repository Structure

```
solution-engineering/
├── Ambient AI Solution/          # AI-powered clinical documentation solutions
│   ├── PythonNotebooks/          # Implementation notebooks
│   └── Readme.md                 # Solution documentation
│
└── RWE-Cohort-Identification/    # Real-world evidence and cohort solutions
    ├── PythonNotebooks/          # Implementation notebooks
    └── requirements.txt          # Python dependencies
```

## Prerequisites

- Python 3.8 or higher
- Jupyter Notebook environment
- Access to IMO Health APIs (contact us for credentials)
- Azure subscription (for cloud-based solutions)

## Contact Information

**IMO Health**

- 🌐 Website: [www.imohealth.com](https://www.imohealth.com)
- 📧 Email: [support@imohealth.com](mailto:support@imohealth.com)
- 💼 LinkedIn: [IMO Health](https://www.linkedin.com/company/imohealth/posts/)

For technical support or partnership inquiries regarding these solutions, please contact our Solution Engineering team at [support@imohealth.com](mailto:support@imohealth.com).

---

## License

Copyright © 2026 IMO Health. All rights reserved.

## About IMO Health

IMO Health is a leading provider of clinical terminology, analytics, and AI-powered solutions for healthcare organizations. Our comprehensive suite of products and services helps healthcare providers improve clinical documentation quality, enhance operational efficiency, and deliver better patient care through advanced data normalization and clinical intelligence.
