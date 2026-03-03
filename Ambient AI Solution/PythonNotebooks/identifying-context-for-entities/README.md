<img src="../static/imo_health.png" alt="IMO Health Logo" width="300"/>

---

# Entity Context Identification & Normalization

## Overview

This notebook demonstrates strategies for identifying and mapping context to clinical entities extracted from medical notes. The workflow focuses on determining the most relevant context for each entity based on the section it appears in and related information from other sections of the clinical note.

The goal is to improve entity normalization accuracy using the IMO Precision Normalize API by providing appropriate contextual information to yield more accurate and specific medical code mappings (ICD-10, SNOMED CT).

### Approaches Compared

1. **Approach 0: Baseline** - No context (baseline comparison)
2. **Approach 1: Dynamic Rules-Based** - Section-specific priority-driven context building
3. **Approach 2: Multi-Context Ensemble** - Per-variation evaluation with individual section contexts

---

## Prerequisites

### Required Software
- **Python 3.8+**
- **Jupyter Notebook** or **VS Code with Jupyter extension**

### Required Python Packages

Install dependencies using pip:

```bash
pip install pandas requests
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

### Required Credentials

#### IMO Precision Normalize API
- **Client ID** and **Client Secret** (configure in notebook)
- API endpoints:
  - Base normalize: `https://api.imohealth.com/precision/normalize`
  - Enrichment: `https://api.imohealth.com/precision/normalize/enrichment`

---

## Input Files

The notebook expects the following files in the current directory:

### 1. Clinical Note Text File
- **Format**: Plain text file containing clinical documentation
- **Examples**: `sample.txt` etc.
- **Location**: Same directory as notebook 

### 2. Entities CSV File
- **Format**: CSV with extracted entities
- **Required Columns**:
  - `entity` - The medical term/entity text
  - `offset` - Character position in note
  - `length` - Entity length in characters
  - `Semantic Tag` - Entity type (e.g., Problem) [optional]
  - `Complete Entity` - Full entity phrase [optional]
- **Examples**: `sample_entities.csv`
- **Location**: Same directory as notebook


### 3. Gold Standard JSON (Optional)
- **Format**: JSON file with expected ICD-10 codes for accuracy calculation
- **Example**: `sample_gold.json`
- **Purpose**: Enables accuracy metrics and performance comparison across approaches

---

## Detailed Approach Descriptions

### Approach 0: Baseline - No Context

**Purpose:**  
Establishes a performance baseline to quantify the improvement gained from contextual enrichment strategies.

**Methodology:**
- Every entity is normalized WITHOUT any surrounding context
- Uses IMO Precision Normalize API base endpoint only
- Returns single best match per entity based solely on string matching

**Advantages:**
- ✅ Simple and fast
- ✅ No preprocessing required
- ✅ Consistent results

**Limitations:**
- ❌ Cannot disambiguate polysemous terms
- ❌ May miss important clinical nuance
- ❌ Lower specificity for complex medical conditions

---

### Approach 1: Dynamic Rules-Based Context with Section-Specific Priorities

**Purpose:**  
Enhanced rule-based approach that dynamically selects the most valuable context sections based on research-driven insights about section-specific information needs.

**Methodology:**
1. **Research-Driven Section Mapping**: Uses empirical data showing which context sections provide the most value
2. **Section-Specific Priority Rules**:
   - **Assessment & Plan entities**: Self-context → HPI → Problem List → History → Physical Exam
   - **Problem List entities**: Self-context → Assessment & Plan → HPI → Reason for Visit
   - **HPI entities**: Self-context → Assessment & Plan → Problem List → Physical Exam
   - **Physical Exam entities**: Self-context → Problem List → HPI
   - **History entities**: Self-context → Problem List
3. **Hierarchical Context Building**: Starts with entity's immediate section, adds sections following priority order up to 1,000-character limit

**Advantages:**
- ✅ Research-backed prioritization improves relevance
- ✅ Self-context emphasis leverages section-specific information density
- ✅ Adaptive to entity location
- ✅ Fast and deterministic
- ✅ No ML infrastructure required

**Limitations:**
- ❌ Priority rules may not generalize to all clinical settings
- ❌ Includes entire sections (may contain some irrelevant content)
- ❌ Requires section headers to be correctly identified

---

### Approach 2: Multi-Context Ensemble with Per-Variation Evaluation

**Purpose:**  
Ensemble approach that evaluates multiple individual section contexts for each entity to determine which specific sections provide the most valuable information.

**Methodology:**
1. **Individual Section Context Generation**: For each entity in a HIGH-VALUE section, generate separate context variations using dynamic section priorities
2. **One Section Per Variation**: Each variation uses ONLY one section's content (not combined)
3. **Parallel Evaluation**: Each entity/context variation is sent to the enrichment API separately
4. **Result Analysis**: Displays top 2 matches per section-context pairing for side-by-side comparison

**Example for entity in "assessment" section:**
- Call 1: Context = Assessment section only
- Call 2: Context = HPI section only
- Call 3: Context = Problem List section only
- Call 4: Context = History section only
- Call 5: Context = Physical Exam section only

**Advantages:**
- ✅ Shows precise impact of each individual section on normalization results
- ✅ Enables evidence-based selection of which sections provide best context
- ✅ Research-validated section priorities ensure relevant sections are evaluated
- ✅ Supports context strategy optimization and refinement

**Limitations:**
- ❌ Higher API costs (5-6× more requests than single-context approaches)
- ❌ Longer processing time due to increased request volume
- ❌ Requires manual review to select final matches

**Key Insight:**  
By evaluating each priority section's context independently, this approach identifies which specific sections provide the most valuable information for entity normalization, enabling data-driven optimization of context selection strategies.

---

## How to Execute

### Step 1: Open the Notebook

**Using Jupyter Notebook:**
```bash
cd /path/to/identifying-context-for-entities/
jupyter notebook entity_context_identification.ipynb
```

**Using VS Code:**
1. Open VS Code
2. Navigate to `entity_context_identification.ipynb`
3. Select Python interpreter (Python 3.8+)
4. Click "Run All" or execute cells sequentially

### Step 2: Configure Input Files

In the initial cells, update the note ID and note type variables:

```python
# Specify your note ID and type
note_id = "sample"           # Your clinical note ID
```

The notebook will automatically construct file paths:
- Clinical note: `{note_id}.txt`
- Entities CSV: `{note_id}_entities.csv`

### Step 3: Execute the Workflow

The notebook is organized into sequential steps:

**Step 1: Load Full Clinical Note**
- Loads clinical note text file
- Loads expected ICD-10 codes from gold standard JSON (optional)
- Displays note statistics

**Step 2: Load Problem Entities via CSV**
- Loads pre-extracted clinical entities from CSV
- Validates entity data structure
- Displays entity statistics

**Step 3: Find Section Headers for Each Entity**
- Identifies clinical note sections (HPI, Assessment, Plan, etc.)
- Maps each entity to its parent section
- Creates section mapping for context building

**Step 4: Strategies for Mapping Entity to Context**
- Defines helper functions for normalization
- Sets up IMO API authentication
- Configures high-value sections for contextual enrichment

**Execute Approaches:**
- **Approach 0**: Baseline - no context for any entity
- **Approach 1**: Dynamic rules-based with section-specific priorities
- **Approach 2**: Multi-context ensemble with per-variation evaluation

**Export Results:**
- Compiles accuracy metrics
- Exports results to CSV files in `results_export/` folder

---

## Expected Outputs

### Console Outputs

Each approach prints:
- Entity-by-entity processing status
- Context used for each entity (if applicable)
- API call details (entity, context length, endpoint used)
- HTML table displaying results with:
  - Input Term
  - Context Used
  - Matched Terms
  - ICD-10 Codes
  - Confidence Scores
- Accuracy metrics (if gold standard codes are provided)

### CSV Export Files

Files are created in `results_export/` folder:

```
results_export/
├── sample_ap_approach-0_results.csv
├── sample_ap_approach-1_results.csv
├── sample_ap_approach-2_results.csv
```

**CSV Format:**
- **Input Term**: Original entity text
- **Context**: Context string used (if any)
- **Matches**: Matched terms with codes and confidence scores

### Results Summary

At the end of execution, a JSON summary is printed showing accuracy metrics for all approaches:

```json
{
  "235-approach-0": { "accuracy": 0.75, ... },
  "235-approach-1": { "accuracy": 0.85, ... },
  "235-approach-2": { "accuracy": 0.90, ... }
}
```

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'pandas'` or similar

**Solution:**
```bash
pip install -r requirements.txt
```
Or install packages individually:
```bash
pip install pandas requests
```

### Issue: File not found error for clinical note or entities CSV

**Solution:** 
- Verify the `note_id` and `note_type` variables are set correctly
- Ensure files exist in expected locations: `{note_id}_{note_type}.txt` and `{note_id}_{note_type}_entities.csv`
- Use absolute paths if needed

### Issue: `401 Unauthorized` from IMO API

**Solution:** Verify `client_id` and `client_secret` are correct in the normalization setup cell.

### Issue: Empty sections dictionary

**Solution:** 
- Verify clinical note contains recognizable section headers
- Check section header regex patterns in the "Find Section Headers" cell
- Note headers should follow standard SOAP note format (e.g., "ASSESSMENT:", "HPI:", etc.)

### Issue: No entities assigned to sections

**Solution:**
- Verify entity offsets are correct in the CSV file
- Ensure offsets correspond to character positions in the clinical note
- Check that entity extraction preserved proper offset values

---

## Performance Comparison

After running all approaches, compare:
- **Accuracy**: Precision of ICD-10 code matches (if gold standard codes provided)
- **Specificity**: Are matched codes more clinically specific with context?
- **Speed**: Execution time per approach
- **Cost**: API call volume and associated costs

**Expected Results:**
- **Approach 0**: Fastest execution, baseline accuracy, single API call per entity
- **Approach 1**: Fast execution, improved accuracy through intelligent section prioritization
- **Approach 2**: Slower execution (multiple API calls per entity), highest insight into section-specific value, enables optimization

**Cost Considerations:**
- **Approach 0**: ~1 API call per entity (base normalize endpoint)
- **Approach 1**: ~1 API call per entity in high-value sections (enrichment endpoint)
- **Approach 2**: ~5-6 API calls per entity (one per priority section for comprehensive analysis)

---

## High-Value Sections

The notebook uses research-driven criteria to identify sections that benefit from contextual enrichment:

**High-Value Sections** (entities receive context):
- Assessment
- Assessment & Plan
- Problem List
- HPI (History of Present Illness)
- Physical Exam
- History
- Review of Systems
- Reason for Visit
- Medical Decision Making
- Patient Instructions
- Follow-up
- Presenting Complaint

**Other Sections** (entities typically normalized without enrichment):
- Past Medical History
- Family/Social/Surgical History
- Current Medications
- Administrative sections

You can customize these section lists in the notebook to match your clinical documentation standards.

---

## Additional Notes

### Privacy & Compliance

⚠️ **IMPORTANT**: This notebook processes clinical data. Ensure:
- PHI/PII data is de-identified before processing
- Compliance with HIPAA, GDPR, or applicable regulations
- Proper data handling agreements with API providers
- Secure storage of API credentials

### Customization

**High-Value Sections:**
Modify the section list to change which sections receive contextual enrichment:
```python
HIGH_VALUE_SECTIONS = set([
    "assessment",
    "impression",
    "chief complaint",
    # Add your custom sections
])
```

**Context Length Limit:**
`MAX_CONTEXT_LENGTH` variable (default: 1000 characters) 

**Section Priority Rules:**
Customize the `build_context_approach_1()` function to modify section-specific priorities based on your clinical workflow.

---

## Next Steps

1. Test with your clinical notes and entity extraction results
2. Measure the impact of different context strategies on normalization accuracy
3. Compare accuracy metrics across approaches
4. Optimize context window sizes and section priorities for your use case
5. Export results for further analysis and reporting

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review notebook markdown cells for detailed step descriptions
3. Verify all prerequisites are installed
4. Check IMO API credentials and quotas
5. Validate input file formats match expected structure

---

## Version History
