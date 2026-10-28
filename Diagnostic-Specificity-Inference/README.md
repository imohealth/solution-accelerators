# Diagnostic Specificity Inference

[![IMO Health](https://img.shields.io/badge/IMO_Health-Knowledge_Graph-7C0EDD)](https://www.imohealth.com/)
[![Scenarios](https://img.shields.io/badge/Inference_Scenarios-9-10b981)](.)
[![LLM](https://img.shields.io/badge/LLM-Claude_Haiku_4.5-57039E)](https://aws.amazon.com/bedrock/)
[![Framework](https://img.shields.io/badge/Framework-LangGraph_ReAct-orange)](https://langchain-ai.github.io/langgraph/)

> **Agentic diagnostic specificity** — 9 inference scenarios that use an LLM agent + IMO Normalize API + IMO Knowledge Graph to refine, rank, and infer diagnoses from clinical notes, medications, procedures, and labs.

Each scenario is a standalone Jupyter notebook with a **LangGraph ReAct agent**, rich streaming HTML output, and direct API calls to the IMO Health platform. They mirror the modes available in the `refine_with_kg` route of the Diagnosis Specificity Agent web application.

---

## Quick Navigation

| # | Scenario | Mode | Notebook | Tools | Link |
|---|----------|------|----------|-------|------|
| 1 | [Diagnosis Specificity using Problems](#1-diagnosis-specificity-using-problems) | `ds-conditions` | [diagnostic_specificity_demo.ipynb](Diagnosis%20Specificity%20using%20Problems/diagnostic_specificity_demo.ipynb) | 4 | <!-- TODO: add GitHub link --> |
| 2 | [Refine Diagnosis using Medication](#2-refine-diagnosis-using-medication) | `refine` | [refine_diagnosis_meds_demo.ipynb](Refine%20Diagnosis%20using%20med/refine_diagnosis_meds_demo.ipynb) | 9 | <!-- TODO: add GitHub link --> |
| 3 | [Rank Diagnosis using Medication](#3-rank-diagnosis-using-medication) | `rank` | [rank_diagnosis_demo.ipynb](Rank%20Diagnosis%20using%20med/rank_diagnosis_demo.ipynb) | 2 | <!-- TODO: add GitHub link --> |
| 4 | [Diagnosis Specificity using Medication](#4-diagnosis-specificity-using-medication) | `dx-infer` | [diagnosis_inference_demo.ipynb](Diagnosis%20Specificity%20using%20med/diagnosis_inference_demo.ipynb) | 2 | <!-- TODO: add GitHub link --> |
| 5 | [Medication Identification](#5-medication-identification) | `med-id` | [medication_identification_demo.ipynb](Medication%20Identification/medication_identification_demo.ipynb) | 3 | <!-- TODO: add GitHub link --> |
| 6 | [Diagnosis to Medication](#6-diagnosis-to-medication) | `dx-to-med` | [diagnosis_to_medication_demo.ipynb](Diagnosis%20to%20Medication/diagnosis_to_medication_demo.ipynb) | 2 | <!-- TODO: add GitHub link --> |
| 7 | [Diagnosis Specificity using Procedure](#7-diagnosis-specificity-using-procedure) | `dx-infer-proc` | [dx_infer_proc_demo.ipynb](Diagnosis%20Specificity%20using%20procedure/dx_infer_proc_demo.ipynb) | 2 | <!-- TODO: add GitHub link --> |
| 8 | [Diagnosis Specificity using Procedure with Temporality](#8-diagnosis-specificity-using-procedure-with-temporality) | `procedure_inference` | [procedure_inference_demo.ipynb](Diagnosis%20Specificity%20using%20Procedure%20with%20Temporality/procedure_inference_demo.ipynb) | 2 | <!-- TODO: add GitHub link --> |
| 9 | [Lab Identification (Prototype)](#9-lab-identification-prototype) | `lab-id` | [lab_identification_demo.ipynb](Lab%20Identification%20(Prototype)/lab_identification_demo.ipynb) | 2 | <!-- TODO: add GitHub link --> |

---

## Inference Scenarios

### Problem-Based

#### 1. Diagnosis Specificity using Problems

**Mode:** `ds-conditions` &nbsp;|&nbsp; **Folder:** `Diagnosis Specificity using Problems/`

Refines a diagnosis extracted from a clinical note using the Knowledge Graph's refinement axes (type, laterality, severity, chronicity, etc.). The agent extracts base problems from a clinical note, presents them for selection, then drills down using refinement groups and sequential narrowing.

**Workflow:**
1. Extract base diagnoses from clinical note (text-only, no tool calls)
2. User selects which diagnosis to refine (interactive HTML radio buttons + local HTTP bridge)
3. Normalize → get refinement groups → match refinements to clinical evidence → resolve via graph traversal → verify ICD-10

| Tool | Purpose |
|------|---------|
| `normalize_medical_term` | Map clinical term → IMO lexical code + ICD-10 (domain: Problem) |
| `get_lexical` | Query KG for concept data including `allowedRefinements` |
| `get_allowed_refinements` | Get refinement groups (type, laterality, severity, etc.) |
| `get_narrower_sequential_refinements` | Apply refinements sequentially to resolve most specific concept |

**Example:** Hypertensive chronic kidney disease → extracts "Hypertension" and "Chronic kidney disease" → refines using laterality, type, and complication axes.

---

### Medication-Based

#### 2. Refine Diagnosis using Medication

**Mode:** `refine` &nbsp;|&nbsp; **Folder:** `Refine Diagnosis using med/`

Two-phase medication-based diagnosis refinement. Phase 1 uses the medication to drill down the diagnosis hierarchy via `domainNarrowerByMedications`. Phase 2 applies remaining note-driven refinement axes one at a time.

**Workflow:**
1. Extract base diagnosis + medications from clinical note
2. **Phase 1:** Normalize both → iteratively call `get_medication_diagnosis_proto` to drill down (medication-guided hierarchy)
3. **Phase 2:** Call `get_allowed_refinements` on reached concept → apply remaining qualifiers one at a time via `get_narrower_sequential_refinements`
4. Verify final diagnosis with ICD-10

| Tool | Purpose |
|------|---------|
| `normalize_medical_term` | Map terms → IMO lexical codes (domain: Problem or Medication) |
| `get_lexical` | Query KG for concept data |
| `get_domain_hierarchy` | Get narrower/broader concepts in the hierarchy |
| `get_treatments_for_problem` | Get associated/contraindicated/supportive treatments |
| `get_caused_problems` | Get complications caused by a condition or medication |
| `get_diagnostics_for_problem` | Get diagnostic tests relevant to a problem |
| `get_allowed_refinements` | Get refinement groups for Phase 2 |
| `get_narrower_sequential_refinements` | Apply refinements sequentially (Phase 2) |
| `get_medication_diagnosis_proto` | Med-guided hierarchy drill-down via `domainNarrowerByMedications` (Phase 1) |

**EXPLICIT DOCUMENTATION RULE:** Only selects candidates justified by: (A) explicitly written in note, (B) directly observable from medication list, (C) medication class identifies disease subtype, or (D) validated clinical assessment tools.

**Example:** Diabetes mellitus + Metformin → Phase 1 drills to "Type 2 diabetes mellitus" (Metformin = type 2 drug) → Phase 2 checks for additional refinement axes.

---

#### 3. Rank Diagnosis using Medication

**Mode:** `rank` &nbsp;|&nbsp; **Folder:** `Rank Diagnosis using med/`

Ranks a list of candidate diagnoses against a medication list using KG `treatedProblems` edges as clinical evidence. Uses a scoring formula with direct match (+0.20), hierarchy match (+0.15), and additional medication support (+0.10) on a 0.50 baseline.

**Workflow:**
1. Normalize each medication (domain: Medication)
2. Query KG for each medication's `treatedProblems`, `preventedProblems`, `causedProblems`
3. Run `_code_based_filter`: normalize candidates (domain: Problem), fetch `domainBroader` parents, do exact code matching
4. Score each candidate using the formula → rank by confidence

| Tool | Purpose |
|------|---------|
| `normalize_medication_only` | Normalize medication terms (domain: Medication) |
| `get_lexical_for_ranking` | Query KG + run `_code_based_filter` against candidates |

**Score Labels:** 0.80–1.00 Strong · 0.60–0.79 Moderate · 0.40–0.59 Neutral · 0.20–0.39 Weak · 0.00–0.19 Contraindicated

**Example:** Candidate diagnoses (paroxysmal atrial fibrillation, ventricular tachycardia, etc.) ranked against Digoxin + Warfarin + Metoprolol → Hypertrophic cardiomyopathy scores 0.90 (Strong).

---

#### 4. Diagnosis Specificity using Medication

**Mode:** `dx-infer` &nbsp;|&nbsp; **Folder:** `Diagnosis Specificity using med/`

Infers the most specific diagnosis from a base diagnosis + medication using a 5-step iterative drill-down via `domainNarrowerByMedications`. Simpler than `refine` mode — focuses solely on medication-guided narrowing without a Phase 2 refinement step.

**Workflow:**
1. Normalize base diagnosis (Problem) and medication (Medication)
2. Iteratively call `get_medication_diagnosis_proto` — pick best match at each level, drill deeper
3. Stop when leaf reached (numberOfDomainChildren = 0) or no further med-linked children
4. Verify final diagnosis with ICD-10

| Tool | Purpose |
|------|---------|
| `normalize_medical_term` | Map terms → IMO lexical codes (domain: Problem or Medication) |
| `get_medication_diagnosis_proto` | Iterative med-guided hierarchy drill-down |

**Example:** Tonsillitis + Amoxicillin → drills down to most specific tonsillitis subtype linked to amoxicillin treatment.

---

#### 5. Medication Identification

**Mode:** `med-id` &nbsp;|&nbsp; **Folder:** `Medication Identification/`

Identifies all dose forms, strengths, and containing medications for a given drug name using the KG medication hierarchy. Useful for medication reconciliation and formulary mapping.

**Workflow:**
1. Normalize the medication term
2. Get dose forms + root-level containing medications via `get_containing_medications`
3. For each containing medication, get the full hierarchy (strengths → dose forms → SCD/SBD names) via `get_hierarchy_for_containing_medication`

| Tool | Purpose |
|------|---------|
| `normalize_medical_term` | Map drug name → IMO lexical code (domain: Medication) |
| `get_containing_medications` | Get dose forms and root-level containing medications |
| `get_hierarchy_for_containing_medication` | Get full 3-level medication hierarchy |

**Example:** "Metformin" → identifies all strengths (500mg, 850mg, 1000mg), dose forms (tablet, extended-release), and branded/generic names.

---

#### 6. Diagnosis to Medication

**Mode:** `dx-to-med` &nbsp;|&nbsp; **Folder:** `Diagnosis to Medication/`

Given a diagnosis, retrieves all associated treatment medications from the Knowledge Graph. Validates diagnosis-to-medication relationships using `associatedTreatments` edges.

**Workflow:**
1. Normalize the diagnosis (domain: Problem)
2. Query `get_treatments_for_problem` — returns associated, contraindicated, and supportive treatments with pagination

| Tool | Purpose |
|------|---------|
| `normalize_medical_term` | Map diagnosis → IMO lexical code (domain: Problem) |
| `get_treatments_for_problem` | Get `associatedTreatments` from KG with pagination |

**Example:** "Type 2 diabetes mellitus" → retrieves Metformin, Insulin glargine, Empagliflozin, and hundreds more associated treatments.

---

### Procedure-Based

#### 7. Diagnosis Specificity using Procedure

**Mode:** `dx-infer-proc` &nbsp;|&nbsp; **Folder:** `Diagnosis Specificity using procedure/`

Infers the most specific diagnosis from a base diagnosis + procedure using `domainNarrowerByProcedures` — the procedure equivalent of medication-guided drill-down.

**Workflow:**
1. Normalize base diagnosis (Problem) and procedure
2. Iteratively call `get_procedure_diagnosis_proto` to drill down via procedure-linked narrower concepts
3. Verify final diagnosis with ICD-10

| Tool | Purpose |
|------|---------|
| `normalize_medical_term` | Map terms → IMO lexical codes |
| `get_procedure_diagnosis_proto` | Procedure-guided hierarchy drill-down via `domainNarrowerByProcedures` |

---

#### 8. Diagnosis Specificity using Procedure with Temporality

**Mode:** `procedure_inference` &nbsp;|&nbsp; **Folder:** `Diagnosis Specificity using Procedure with Temporality/`

Extends procedure-based inference with temporality awareness — considers whether the procedure was performed before, during, or after the encounter to refine the diagnosis accordingly.

**Workflow:**
1. Normalize diagnosis and procedure
2. Drill down using procedure-linked hierarchy with temporal context
3. Apply temporality-based refinement logic

| Tool | Purpose |
|------|---------|
| `normalize_medical_term` | Map terms → IMO lexical codes |
| `get_procedure_diagnosis_proto` | Procedure-guided drill-down with temporal context |

---

### Lab-Based

#### 9. Lab Identification (Prototype)

**Mode:** `lab-id` &nbsp;|&nbsp; **Folder:** `Lab Identification (Prototype)/`

Normalizes lab test names and explores the lab hierarchy in the Knowledge Graph. Prototype scenario for lab-based diagnosis inference.

**Workflow:**
1. Normalize lab term (domain: Lab, with optional `order_name`)
2. Explore lab concept hierarchy in the KG

| Tool | Purpose |
|------|---------|
| `normalize_medical_term` | Map lab name → IMO lexical code (domain: Lab) |
| KG hierarchy queries | Explore lab concept relationships |

---

## Prerequisites

### Python Packages

```bash
pip install langchain-aws langgraph requests ipython
```

### Credentials

Each notebook requires four sets of credentials:

| Credential | Environment Variable | Purpose |
|-----------|---------------------|---------|
| IMO Normalize API | `IMO_NORMALIZE_CLIENT_ID`, `IMO_NORMALIZE_SECRET` | OAuth2 client credentials for Precision Normalize |
| IMO Knowledge Graph | `IMO_KG_CLIENT_ID`, `IMO_KG_CLIENT_SECRET` | OAuth2 client credentials for GOAT GraphQL API |
| AWS Bedrock | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | STS temporary credentials for Claude Haiku access |
| AWS Region | `AWS_DEFAULT_REGION` | Must be `us-east-1` |

> **Security Note:** Remove all hardcoded credentials before pushing to any remote repository. Use environment variables or AWS SSM Parameter Store in production.

### Shared Support Files

Each notebook folder contains these support files:

| File | Purpose |
|------|---------|
| `kg_config.py` | Reads credentials from environment variables or AWS SSM |
| `kg_api_client.py` | Direct HTTP client for IMO Normalize + KG GraphQL APIs with OAuth token caching |

---

## How to Run

1. Open any notebook folder in VS Code or JupyterLab
2. Set credentials as environment variables (or edit the setup cell)
3. Run all cells — the agent streams results with live HTML output
4. For interactive notebooks (e.g., `ds-conditions`), click the HTML button to select a diagnosis to refine

---

## Related Resources

- [Solution Accelerators (main README)](../Readme.md) — Full catalog of IMO Health solution accelerators
- [Best Practices Guide](best_practices.md) — How to build your own DS Agent for these inference scenarios
- [IMO KG Studio](https://studio.imohealth.com/) — Explore the Knowledge Graph interactively
