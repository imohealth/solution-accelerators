---
name: normalize-term
description: Normalize medical terms to IMO lexical codes with ICD-10, SNOMED CT, and other code mappings.
---

# Normalize Medical Term

Normalize one or more medical terms using the IMO Precision Normalize API and retrieve standardized code mappings.

## Workflow

1. **Ask the user** for the medical term(s) they want to normalize and the domain. If the domain is not specified, default to "Problem". Valid domains: Problem, Procedure, Medication, Lab.

2. **Normalize** the term(s) using `normalize-ppml___normalize_ppml_term`:
   - Pass the terms as an array of strings
   - Set the domain to the user's specified domain

3. **Retrieve mappings** for each normalized result using `graphql-modifier___get_mappings`:
   - Use the `lexical_code` (NOT `imo_code`) from normalization results
   - Set the domain to match the normalization domain
   - Optionally filter by specific code systems if the user requested them (e.g., icd10cm, snomedInternational, rxnorm, cpt)

4. **Present results** in a clear table format showing:
   - Input term
   - IMO lexical title and code
   - Mapped codes (ICD-10-CM, SNOMED CT, etc.) with relationship types
   - Confidence/match quality when available

## Tips
- For Medication domain, the API returns up to 20 results per term — help the user pick the best match.
- For Problem/Procedure/Lab domains, the API returns 1 result per term.
- Use `core-search___get_term_detail` for additional supplemental information on any IMO lexical code.
- Remind users: confirm results against clinical documentation and organizational coding policies.
