---
name: entity-extraction
description: Extract clinical entities (problems, medications, labs, allergens) from free-text clinical notes using IMO CCP NLP.
---

# Clinical Entity Extraction

Extract and classify clinical entities from unstructured medical text using IMO's CCP NLP engine.

## Workflow

1. **Get the clinical text** from the user. This can be a discharge summary, progress note, consultation report, or any clinical narrative.

2. **Extract entities** using `ccp___entity_extraction`:
   - Pass the full text as the `text` parameter
   - Use default version (3.0) unless the user specifies otherwise

3. **Organize the results** by entity type:
   - **Problems/Diagnoses** — conditions, symptoms, findings
   - **Medications** — drugs, dosages, routes
   - **Lab Results** — lab tests, values, units
   - **Allergens** — allergies and adverse reactions

4. **Present results** in a structured format showing:
   - Entity text as found in the source
   - Entity type/category
   - Mapped codes: ICD-10-CM, SNOMED CT, UMLS, IMO lexical codes
   - Confidence/semantic information when available

5. **Optional enrichment**: For any extracted entity, offer to:
   - Normalize it further with `normalize-ppml___normalize_ppml_term`
   - Get detailed info with `core-search___get_term_detail`
   - Find specificity paths with `graphql-modifier___get_lexical` and `graphql-modifier___get_narrower_hierarchy`
   - Categorize extracted problems with `categorize___categorize_problems`

## Tips
- Works best with clinical narrative text (not structured data or codes).
- For batch processing of multiple notes, process them sequentially.
- Remind users: extracted entities should be verified against the source documentation.
