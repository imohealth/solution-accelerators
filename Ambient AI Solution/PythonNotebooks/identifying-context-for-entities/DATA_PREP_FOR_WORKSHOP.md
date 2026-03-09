# Data Preparation for Entity Context Identification Workshop

## Overview

This document outlines the data prerequisites needed to successfully run the `entity_context_identification.ipynb` notebook. The notebook analyzes clinical notes to identify optimal `<entity, context>` pairs that improve normalization accuracy when converting free-text clinical terms to standardized medical codes (ICD-10, SNOMED CT).

## Prerequisites

To run this notebook effectively, customers must prepare **multiple clinical notes** with corresponding entity extractions and gold standard data. The more notes provided, the better the notebook can identify patterns for the specific note style.

---

## Required Data Files

For each clinical note, you need to provide **three files**:

### 1. Clinical Note Text File (`.txt`)

**Format:** Plain text file
**Naming Convention:** `{note_id}.txt` (e.g., `sample.txt`, `sample2.txt`)

**Description:**
The complete clinical note text containing structured medical documentation with sections such as:
- History of Present Illness (HPI)
- Assessment
- Assessment and Plan
- Physical Exam
- Problem List
- Reason for Visit
- Review of Systems
- Past Medical History

**Example:**
```
ASSESSMENT:
58-year-old male with hypertension and heart failure.

HISTORY OF PRESENT ILLNESS:
Patient is a 58-year-old male with history of hypertension and chronic systolic
heart failure presenting with worsening shortness of breath...

PHYSICAL EXAM:
Blood pressure 145/88, heart rate 98...

PROBLEM LIST:
- Hypertension
- Heart Failure
```

---

### 2. Extracted Entities CSV File (`.csv`)

**Format:** CSV file with specific columns
**Naming Convention:** `{note_id}_entities.csv` (e.g., `sample_entities.csv`)

**Required Columns:**
- `entity` - The text span of the clinical term (e.g., "chest pain", "hypertension")
- `offset` - Character position where the entity starts in the note (integer)
- `length` - Number of characters in the entity text (integer)

**Optional Columns:**
- `Semantic Tag` - Entity type (e.g., problem, medication, procedure)

**Example:**
```csv
entity,offset,length
hypertension,34,12
heart failure,51,13
shortness of breath,906,19
dyspnea on exertion,1047,19
bilateral lower extremity swelling,1134,34
```

**How to Generate:**
This file is generated using Named Entity Recognition (NER) systems such as:
- IMO's entity extraction API
- Custom NER tools
- Medical NLP pipelines

The `offset` value must accurately reflect the character position in the original `.txt` file to enable proper section mapping.

---

### 3. Gold Standard ICD-10 Codes (`.json`)

**Format:** JSON file containing an array of ICD-10 codes
**Naming Convention:** `{note_id}_gold.json` (e.g., `sample_gold.json`)

**Description:**
This file contains the **expected encounter diagnosis codes** (the final outcome of the note) that should be identified through entity extraction and normalization. These represent the clinically accurate diagnoses for the patient encounter.

**Example:**
```json
[
  "I10",
  "I50.23"
]
```

**ICD-10 Code Descriptions:**
- `I10` - Essential (primary) hypertension
- `I50.23` - Acute on chronic systolic (congestive) heart failure

**Purpose:**
The gold standard codes enable the notebook to:
- Calculate normalization accuracy metrics
- Evaluate which context strategies yield the best results
- Identify true positives, false positives, and false negatives
- Recommend optimal `<entity, context>` pairs

---

## Minimum Data Requirements

### For Basic Testing:
- **1-2 clinical notes** with corresponding entities and gold standards

### For Effective Pattern Identification:
- **5-10 clinical notes** with diverse clinical scenarios
- Notes should represent the typical documentation style and structure used in your organization

### For Production-Ready Recommendations:
- **10+ clinical notes** covering various:
  - Clinical specialties
  - Note types (outpatient, inpatient, ED)
  - Documentation patterns
  - Complexity levels

---

## Data Quality Guidelines

### Clinical Notes:
- Should contain clearly delineated sections with headers
- Represent realistic clinical documentation
- Include diverse clinical scenarios and diagnoses
- Maintain consistent formatting across notes

### Extracted Entities:
- All clinically significant problems, diagnoses, and symptoms should be extracted
- Offset values must be accurate (validated against source text)
- Should include entities from all relevant sections (not just Assessment/Plan)

### Gold Standard Codes:
- Must represent the **final encounter diagnosis** (the billable/documentable diagnoses)
- Should be comprehensive (include all relevant diagnoses from the encounter)
- Use specific ICD-10 codes (not unspecified codes when specific ones apply)
- Verified by clinical or coding experts

---

## How the Notebook Uses This Data

The notebook follows this workflow:

1. **Loads Clinical Note** (`.txt`) and Gold Standard (`.json`)
2. **Loads Extracted Entities** (`.csv`)
3. **Maps Entities to Sections** - Identifies which section each entity appears in
4. **Tests Multiple Context Strategies:**
   - **Approach 0:** No context (baseline)
   - **Approach 1:** Rules-based context with section-specific priorities
   - **Approach 2:** Multi-context ensemble testing multiple section combinations
5. **Normalizes Entities** - Converts entities to ICD-10/SNOMED codes using IMO Precision Normalize API
6. **Evaluates Results** - Compares normalized codes against gold standard
7. **Recommends Best `<entity, context>` Pairs** - Identifies which context sections yield highest accuracy

---

## Expected Outputs

After running the notebook with your data, you will receive:

1. **Accuracy Metrics** - Precision, recall, and F1 scores for each approach
2. **Ranked Context Strategies** - Which section combinations work best for your note style
3. **Entity-Section Mapping** - Distribution of entities across clinical sections
4. **Detailed Results CSV Files** - Exportable results for further analysis
5. **Recommended Context Rules** - Production-ready configuration for entity normalization

---

## File Organization Example

The notebook expects all sample data files to be in a `sample_data/` folder:

```
/your-project-directory/
├── sample_data/
│   ├── note001.txt
│   ├── note001_entities.csv
│   ├── note001_gold.json
│   ├── note002.txt
│   ├── note002_entities.csv
│   ├── note002_gold.json
│   ├── note003.txt
│   ├── note003_entities.csv
│   └── note003_gold.json
└── entity_context_identification.ipynb
```

**Note:** The notebook is configured to automatically look for files in the `sample_data/` subdirectory. All your clinical notes, entities, and gold standard files should be placed in this folder.

---

## Getting Started

1. Prepare your clinical notes in `.txt` format
2. Extract entities using your NER system and save as `.csv`
3. Work with clinical/coding experts to create gold standard `.json` files
4. Place all files in the `sample_data/` folder within the notebook directory
5. Update the `note_id` variable in the notebook to match your file naming convention (e.g., "sample" or "sample2")
6. Run the notebook cells sequentially
7. Review accuracy results and recommended context strategies

---

## Questions or Issues

If you have questions about data preparation or encounter issues:
- Verify file naming conventions match the `{note_id}` pattern
- Ensure CSV offset values are accurate
- Confirm gold standard codes represent encounter diagnoses (not all mentioned conditions)
- Validate that clinical notes contain clear section headers
