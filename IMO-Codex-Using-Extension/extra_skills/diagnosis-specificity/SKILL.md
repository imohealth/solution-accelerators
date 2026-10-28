---
name: diagnosis-specificity
description: Find the most specific ICD-10 code for a diagnosis by navigating the IMO Knowledge Graph hierarchy and applying refinements.
---

# Diagnosis Specificity Agent

Navigate the IMO Knowledge Graph to find the most specific ICD-10 code for a given diagnosis. This skill chains multiple tools to drill from a general term to the most clinically precise code.

## Workflow

1. **Get the diagnosis** from the user. Ask for any known qualifiers (laterality, chronicity, severity, anatomical site, etc.).

2. **Normalize** the term using `normalize-ppml___normalize_ppml_term`:
   - Domain: "Problem"
   - Extract the `lexical_code` from the result

3. **Explore the lexical** using `graphql-modifier___get_lexical`:
   - Use the `lexical_code` from step 2
   - Review the broader concepts, applied refinements, and allowed refinements

4. **Check allowed refinements** using `graphql-modifier___get_allowed_refinements`:
   - Review refinement groups (laterality, chronicity, severity, type, etc.)
   - Ask the user to confirm which refinements apply to their case if not already specified

5. **Drill down** using `graphql-modifier___get_narrower_sequential_refinements`:
   - Apply the selected refinement codes as a nested sequence
   - Set `include_mappings: true` to get ICD-10 codes at the deepest level
   - Set `include_allowed_refinements: true` to check if further refinement is possible

6. **If further specificity exists**, repeat steps 4-5 on the narrower lexical.

7. **Retrieve final mappings** using `graphql-modifier___get_mappings`:
   - Get ICD-10-CM, SNOMED CT, and other code system mappings
   - Set `include_hcc: true` if HCC risk data is relevant

8. **Present the specificity path** showing:
   - Starting term → intermediate refinements → most specific lexical
   - Final ICD-10-CM code(s) with relationship type (exactMatch preferred)
   - HCC risk category if requested
   - Any remaining allowed refinements the user could apply

## Important
- Always use `lexical_code`, never `imo_code`, as the input for Knowledge Graph tools.
- Remind users: do not infer undocumented specificity. Confirm against clinical documentation.
