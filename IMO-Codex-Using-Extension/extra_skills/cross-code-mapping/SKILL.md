---
name: cross-code-mapping
description: Map between clinical code systems — ICD-10-CM, SNOMED CT, CPT, RxNorm, HCPCS, LOINC, and more.
---

# Cross-Code Mapping

Translate medical codes between industry standard coding systems using the IMO Knowledge Graph.

## Supported Code Systems

| Domain | Code Systems |
|---|---|
| Problem | ICD-10-CM, ICD-10-CA, ICD-9-CM, SNOMED CT, DSM-5, ICD-O, MONDO |
| Procedure | CPT, HCPCS, ICD-10-PCS, LOINC, SNOMED CT |
| Medication | RxNorm, NDC, CVX, SNOMED CT |

## Workflow

1. **Get the input** from the user:
   - The source code or medical term
   - The source code system (if known)
   - The target code system(s) they want to map to

2. **Normalize the term** (if starting from free text) using `normalize-ppml___normalize_ppml_term`:
   - Determine the correct domain (Problem, Procedure, Medication, Lab)
   - Extract the `lexical_code` from the result

3. **If starting from a known code**, use `core-search___lookup_term_by_code` or `core-search___search_medical_term` to find the IMO lexical code first.

4. **Retrieve mappings** using `graphql-modifier___get_mappings`:
   - Use the `lexical_code` (NOT `imo_code`)
   - Set the domain to match the term's domain
   - Filter by target code systems using the `code_systems` parameter if the user only needs specific systems
   - Set `include_hcc: true` for Problem domain if HCC data is relevant

5. **Present results** showing:
   - Source term/code
   - Each target code system mapping with: code, title, relationship type (exactMatch, closeMatch, broadMatch, narrowMatch, relatedMatch)
   - Flag `narrowMatch` and `broadMatch` results — these may need clinical review

## Relationship Types
- **exactMatch**: Equivalent meaning in both systems
- **closeMatch**: Nearly equivalent, minor differences
- **broadMatch**: Target code is more general than source
- **narrowMatch**: Target code is more specific than source
- **relatedMatch**: Related but not directly equivalent
