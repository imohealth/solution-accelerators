<img src="../static/imo_health.png" alt="IMO Health Logo" width="300"/>

---

# Precision Normalize — Enrichment

**Products:** IMO Precision Normalize

This folder contains a single notebook that demonstrates context-aware clinical term normalization using the IMO Precision Normalize Enrichment API.

---

## Notebooks

### 1. `01_IMO_Enrichment_Normalize.ipynb`
**Product:** IMO Precision Normalize

Submits clinical terms alongside contextual metadata to the Enrichment endpoint and compares results against base normalization.

What it does:
- Installs dependencies and loads `precision_normalize` credentials from `config.json`
- Authenticates with the IMO OAuth endpoint
- Accepts a list of clinical terms with optional `context` fields (e.g. patient age, care setting, specialty)
- POSTs each term to the `/precision/normalize/enrichment` endpoint
- Parses enriched mappings and compares them side-by-side against base normalization results
- Highlights cases where enrichment changed or refined the normalized concept
- Flags refineable concepts for review
- Exports a final comparison DataFrame

---

## When to use this notebook

Use the Enrichment endpoint when:
- Clinical terms are ambiguous and context (e.g. care setting or specialty) can disambiguate them
- You want to compare enriched vs. base normalization before committing to a coding workflow
- You need richer metadata mappings than base normalization provides

---

## Configuration

Copy `config.json.template` to `config.json` and fill in your credentials:

```json
{
  "precision_normalize": {
    "client_id": "YOUR_PRECISION_NORMALIZE_CLIENT_ID",
    "client_secret": "YOUR_PRECISION_NORMALIZE_CLIENT_SECRET"
  }
}
```

> ⚠️ Never commit `config.json` to source control.
