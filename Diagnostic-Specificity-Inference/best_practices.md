# Best Practices — Building Diagnostic Specificity Inference Agents

This document covers the lessons learned, patterns, and rules to follow when building or modifying any of the **9 diagnostic specificity inference scenarios**. It's organized by topic so you can jump to what you need.

Each scenario uses a **LangGraph ReAct agent** that calls IMO Normalize + Knowledge Graph APIs via purpose-built tools. The scenarios differ in which KG edges they traverse and how many tools the agent needs, but the core patterns are shared.

---

## Table of Contents

1. [Inference Scenario Patterns](#1-inference-scenario-patterns)
2. [Agent Design](#2-agent-design)
3. [System Prompt Writing](#3-system-prompt-writing)
4. [Tool Design](#4-tool-design)
5. [API Client & Authentication](#5-api-client--authentication)
6. [GraphQL Query Construction](#6-graphql-query-construction)
7. [Handling the Narrower Sequential Refinements](#7-handling-the-narrower-sequential-refinements)
8. [Streaming & Real-Time UI](#8-streaming--real-time-ui)
9. [Error Handling](#9-error-handling)
10. [Conversation Management](#10-conversation-management)
11. [Security](#11-security)
12. [Testing & Debugging](#12-testing--debugging)
13. [Performance](#13-performance)
14. [Common Mistakes to Avoid](#14-common-mistakes-to-avoid)

---

## 1. Inference Scenario Patterns

All 9 scenarios share the same foundation — **LangGraph `create_react_agent`** + **IMO Normalize API** + **IMO Knowledge Graph GraphQL** — but they differ in which KG edges they traverse and how the system prompt guides the agent.

### Scenario Overview

| # | Scenario | GraphQL Edge | Tools | Complexity |
|---|----------|-------------|-------|------------|
| 1 | Diagnosis Specificity using Problems | `refinementNarrower` | **4** — `normalize_medical_term`, `get_lexical`, `get_allowed_refinements`, `get_narrower_sequential_refinements` | High — multi-step refinement groups |
| 2 | Refine Diagnosis using Medication | `domainNarrowerByMedications` + `refinementNarrower` | **9** — `normalize_medical_term`, `get_lexical`, `get_domain_hierarchy`, `get_treatments_for_problem`, `get_caused_problems`, `get_diagnostics_for_problem`, `get_allowed_refinements`, `get_narrower_sequential_refinements`, `get_medication_diagnosis_proto` | Highest — two-phase (med drill-down + refinement) |
| 3 | Rank Diagnosis using Medication | `treatedProblems` / `preventedProblems` / `causedProblems` | **3** — `normalize_medication_only`, `get_lexical_for_ranking`, `get_domain_hierarchy` | Medium — scoring formula |
| 4 | Diagnosis Specificity using Medication | `domainNarrowerByMedications` | **2** — `normalize_medical_term`, `get_medication_diagnosis_proto` | Low — iterative drill-down |
| 5 | Medication Identification | `domainNarrower` + `containingMedications` | **3** — `normalize_medical_term`, `get_containing_medications`, `get_hierarchies_for_containing_medications` | Medium — medication hierarchy |
| 6 | Diagnosis to Medication | `associatedTreatments` | **2** — `normalize_medical_term`, `validate_medication_association` | Low — single KG lookup |
| 7 | Diagnosis Specificity using Procedure | `domainNarrowerByProcedures` | **2** — `normalize_medical_term`, `find_diagnosis_by_procedure` | Low — iterative drill-down |
| 8 | DS using Procedure with Temporality | `domainNarrowerByProcedures` + temporal logic | **2** — `normalize_medical_term`, `find_temporal_diagnoses` | Medium — adds temporal context |
| 9 | Lab Identification (Prototype) | `domainNarrower` (Lab domain) | **2** — `normalize_medical_term`, `identify_lab` | Low — lab hierarchy exploration |

### Mode 1: Diagnosis Specificity using Problems (`ds-conditions`)

**Tools:** `normalize_medical_term`, `get_lexical`, `get_allowed_refinements`, `get_narrower_sequential_refinements`

#### KG GraphQL Schemas

**`get_lexical` — Full concept lookup with refinements, hierarchy, and mappings:**

```graphql
query GetLexical($code: String!, $domain: IMODomain!) {
  lexical(code: $code, domain: $domain) {
    code
    title
    synonyms { code title }
    ... on ProblemLexical {
      domainBroader(offset: 0, size: 1000) { code title }
      domainNarrower(offset: 0, size: 1000) { code title }
      mappings { code title codeSystem relationshipType }
      appliedRefinements(offset: 0, size: 1000) { code title group { code title } }
      allowedRefinements(offset: 0, size: 1000) { code title group { code title } }
      refinementFamilies(offset: 0, size: 1000) { code title lexicals { code title } }
    }
  }
}
```

**`get_allowed_refinements` — Refinement groups only (lighter query):**

```graphql
query GetAllowedRefinements($code: String!, $domain: IMODomain!) {
  lexical(code: $code, domain: $domain) {
    code
    title
    ... on ProblemLexical {
      allowedRefinements(offset: 0, size: 1000) { code title group { code title } }
    }
  }
}
```

**`get_narrower_sequential_refinements` — Nested refinement drill-down (dynamically built, max 3 levels per query):**

```graphql
query GetRefinedNarrower($code: String!, $domain: IMODomain!, $ref0: [String!], $ref1: [String!], $ref2: [String!]) {
  lexical(code: $code, domain: $domain) {
    code
    title
    ... on ProblemLexical {
      refinementNarrower(refinements: $ref0, offset: 0, size: 1000) {
        code
        title
        ... on ProblemLexical {
          appliedRefinements { code title }
          refinementNarrower(refinements: $ref1, offset: 0, size: 1000) {
            code
            title
            ... on ProblemLexical {
              appliedRefinements { code title }
              refinementNarrower(refinements: $ref2, offset: 0, size: 1000) {
                code
                title
                ... on ProblemLexical {
                  appliedRefinements { code title }
                  allowedRefinements(offset: 0, size: 1000) { code title group { code title } }
                  mappings { code title codeSystem relationshipType }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

> **Batching:** If >3 refinement steps, they are batched in groups of 3 — each batch resolves to a single code used as the starting point for the next batch. The innermost level of the LAST batch includes `appliedRefinements`, `allowedRefinements`, and `mappings`; intermediate levels only include `appliedRefinements`.

> **Note:** `normalize_medical_term` uses the REST-based Normalize API, not GraphQL.

#### Edge Cases

| Edge Case | Behavior |
|-----------|----------|
| **Pagination overflow** | All list fields (`domainBroader`, `domainNarrower`, `appliedRefinements`, `allowedRefinements`, `refinementFamilies`) use `offset/size: 1000` with automatic page-fetch if 1000 items returned |
| **GraphQL depth limit (max 7)** | `refinementNarrower` nesting capped at 3 levels per query; >3 refinements are auto-batched and chained across multiple queries |
| **Partial resolution** | When a refinement step returns empty `refinementNarrower: []`, the agent reports the deepest concept reached — not a failure |
| **Refinement ordering** | Must follow clinical hierarchy: type → complication → laterality → severity → qualifier. Different orderings may produce different or empty results |
| **Broad terms** | `get_lexical` includes `domainNarrower` which can return hundreds of items for broad terms like "diabetes" — pagination handles this but response is still large for the LLM |
| **No matching refinement** | If a refinement code doesn't exist in the concept's `allowedRefinements`, `refinementNarrower` returns empty — the agent should try alternative refinement codes or report the best match reached |

### Mode 2: Refine Diagnosis using Medication (`refine`)

**Tools:** `normalize_medical_term`, `get_lexical`, `get_domain_hierarchy`, `get_treatments_for_problem`, `get_caused_problems`, `get_diagnostics_for_problem`, `get_allowed_refinements`, `get_narrower_sequential_refinements`, `get_medication_diagnosis_proto`

#### KG GraphQL Schemas

**`get_lexical`** — Same as Mode 1 (full concept lookup with refinements, hierarchy, mappings).

**`get_allowed_refinements`** — Same as Mode 1 (refinement groups only).

**`get_narrower_sequential_refinements`** — Same as Mode 1 (nested refinement drill-down, max 3 levels).

**`get_domain_hierarchy` — Narrower or broader concepts with synonyms:**

```graphql
query GetDomainNarrower($code: String!, $domain: IMODomain!) {
  lexical(code: $code, domain: $domain) {
    code
    title
    synonyms { code title }
    ... on ProblemLexical {
      domainNarrower(offset: 0, size: 1000) { code title }
    }
  }
}
```

> Also supports `domainBroader` via `direction="broader"` parameter.

**`get_treatments_for_problem` — Associated and supportive treatments:**

```graphql
query GetTreatments($code: String!, $domain: IMODomain!) {
  lexical(code: $code, domain: $domain) {
    code
    title
    ... on ProblemLexical {
      numberOfAssociatedTreatments
      numberOfSupportiveTreatments
      associatedTreatments(offset: 0, size: 1000) {
        ... on Lexical { code title }
        ... on MedicationLexical { code title }
      }
    }
  }
}
```

> Separately paginates `supportiveTreatments` in a second query.

**`get_caused_problems` — Caused problems and causative agents (Problem domain):**

```graphql
query GetCausedProblems($code: String!, $domain: IMODomain!) {
  lexical(code: $code, domain: $domain) {
    code
    title
    ... on ProblemLexical {
      numberOfCausedProblems
      numberOfCausativeAgents
      causedProblems(offset: 0, size: 1000) { code title }
    }
  }
}
```

> For Medication domain, uses `... on MedicationLexical` instead. Problem domain also paginates `causativeAgents` separately.

**`get_diagnostics_for_problem` — Associated diagnostic procedures:**

```graphql
query GetDiagnostics($code: String!, $domain: IMODomain!) {
  lexical(code: $code, domain: $domain) {
    code
    title
    ... on ProblemLexical {
      numberOfAssociatedProcedures
      associatedProcedures(offset: 0, size: 1000) { code title }
    }
  }
}
```

**`get_medication_diagnosis_proto` — Medication-guided hierarchy drill-down (Phase 1):**

```graphql
{
  lexical(code: "<diagnosis_code>", domain: problem) {
    title
    ... on ProblemLexical {
      domainNarrowerByMedications(medications: ["<med_code1>", "<med_code2>"], offset: 0, size: 1000) {
        code
        title
        ... on ProblemLexical {
          numberOfDomainChildren
        }
      }
    }
  }
}
```

> **Note:** This query uses string interpolation (not variables) for `diagnosis_code` and `medications` — matching the source implementation.

#### Edge Cases

| Edge Case | Behavior |
|-----------|----------|
| **Two-phase workflow** | Phase 1 (`get_medication_diagnosis_proto`) drills down using medication evidence; Phase 2 (`get_allowed_refinements` + `get_narrower_sequential_refinements`) applies remaining note-driven refinement axes |
| **Phase 1 empty result** | If `domainNarrowerByMedications` returns empty list, the medication has no KG link to the diagnosis hierarchy — agent skips to Phase 2 using the original base concept |
| **Phase 1 leaf detection** | Drill-down stops when `numberOfDomainChildren` is 0 or missing — concept is a leaf |
| **`get_caused_problems` dual domain** | Uses `ProblemLexical` fragment for Problem domain (includes `causativeAgents`), `MedicationLexical` fragment for Medication domain (no `causativeAgents`) |
| **`get_treatments_for_problem` dual pagination** | `associatedTreatments` and `supportiveTreatments` are paginated in separate query loops |
| **Pagination on all list fields** | All tools use `offset/size: 1000` with automatic page-fetch |
| **9-tool complexity** | The LLM must decide which of 9 tools to call — clear system prompt and docstrings are critical to prevent confusion |

---

#### Mode 3 — `rank` (Rank Diagnosis using Medication)

**Tools:** `normalize_medication_only`, `get_lexical_for_ranking`, `get_domain_hierarchy`

#### KG GraphQL Schemas

**`normalize_medication_only`** — REST only (no GraphQL). Calls the Normalize API with `domain: "Medication"` hardcoded. Same REST schema as `normalize_medical_term` but restricted to Medication domain only.

**`get_lexical_for_ranking`** — Calls `get_lexical()` with the **MedicationLexical** fragment, then applies `_code_based_filter` for accurate scoring against candidate diagnoses.

**Stage 1 — Fetch medication's treated/caused problems:**

```graphql
query GetLexical($code: String!, $domain: IMODomain!) {
  lexical(code: $code, domain: $domain) {
    code
    title
    synonyms { code title }
    ... on MedicationLexical {
      mappings { code title codeSystem relationshipType }
      treatedProblems(offset: 0, size: 1000) { code title }
      causedProblems(offset: 0, size: 1000) { code title }
    }
  }
}
```

> **Pagination:** If `treatedProblems` or `causedProblems` returns 1000 items, auto-fetches subsequent pages with increasing `offset` until `len(page) < SIZE`.

**Stage 2 — `_code_based_filter` (runs internally when list exceeds 200 items):**

For each candidate diagnosis:
1. Normalize → `normalize_medical_term(candidate, "Problem")` → gets IMO lexical code
2. Get parent codes → `get_domain_hierarchy(code, "broader", "Problem")`:

```graphql
query GetDomainBroader($code: String!, $domain: IMODomain!) {
  lexical(code: $code, domain: $domain) {
    code
    title
    synonyms { code title }
    ... on ProblemLexical {
      domainBroader(offset: 0, size: 1000) { code title }
    }
  }
}
```

3. Exact code matching: candidate code OR any `domainBroader` parent code found in KG `treatedProblems`/`causedProblems` list → **match**

**`get_domain_hierarchy`** — Same schema as documented in Mode 2 (`domainNarrower` or `domainBroader` with pagination on `ProblemLexical`).

#### Edge Cases

| Edge Case | Behavior |
|-----------|----------|
| **Large KG lists (200+ items)** | `_code_based_filter` activates only when `treatedProblems` or `causedProblems` exceeds `_KG_LIST_THRESHOLD` (200) — otherwise returns full list for the agent to score directly |
| **Code-based matching, not text** | Candidates are normalized to IMO codes, then matched by exact code — avoids false negatives from text mismatch (e.g., "CHF" matches "congestive heart failure" via shared IMO code) |
| **Hierarchy matching** | If a candidate's direct code isn't in the KG list, its `domainBroader` parent codes are also checked — catches hierarchy-level matches |
| **Scoring formula** | Baseline 0.50 + direct match (+0.20) + hierarchy match (+0.15) + additional medication support (+0.10). Labels: 0.80–1.00 Strong, 0.60–0.79 Moderate, 0.40–0.59 Neutral, 0.20–0.39 Weak, 0.00–0.19 Contraindicated |
| **Medication-only normalize** | `normalize_medication_only` refuses non-medication terms — returns error if input is empty |
| **Unmatched candidates** | Candidates with no code match in KG are reported as `_unmatched_candidates` and scored Neutral (0.50) |

---

#### Mode 4 — `dx-infer` (Diagnosis Specificity using Medication)

**Tools:** `normalize_medical_term`, `get_medication_diagnosis_proto`

#### KG GraphQL Schemas

**`normalize_medical_term`** — REST only (no GraphQL). Same Normalize API as Mode 1. Called twice: once with `domain="Problem"` for the base diagnosis, once with `domain="Medication"` for each medication.

**`get_medication_diagnosis_proto`** — Iterative medication-guided drill-down via `domainNarrowerByMedications`:

```graphql
{
  lexical(code: "{diagnosis_code}", domain: problem) {
    title
    ... on ProblemLexical {
      domainNarrowerByMedications(medications: [{medications_arg}], offset: {offset}, size: {SIZE}) {
        code
        title
        ... on ProblemLexical {
          numberOfDomainChildren
        }
      }
    }
  }
}
```

> **Note:** Uses string interpolation (not GraphQL variables) for `diagnosis_code` and `medications` — matching the source implementation. Pagination via `offset/size: 1000` with auto-fetch loop.

> **Result sorting:** The tool wrapper sorts returned items by `numberOfDomainChildren` descending — non-leaf concepts (drillable) appear first, ensuring they are visible even when the list is truncated.

#### Edge Cases

| Edge Case | Behavior |
|-----------|----------|
| **Iterative drill-down** | Agent calls `get_medication_diagnosis_proto` repeatedly — picks best candidate at each level based on clinical note context, drills deeper until leaf reached |
| **Leaf detection** | Stops when `numberOfDomainChildren` is `0` or missing/null — concept is a leaf with no further narrower children |
| **Max iterations** | System prompt caps at 8 drill-down rounds to prevent infinite loops |
| **Empty result at any level** | If `domainNarrowerByMedications` returns empty list, agent backs up and uses the last non-empty concept as final diagnosis |
| **No Phase 2** | Unlike Mode 2 (`refine`), this mode has NO Phase 2 refinement step — focuses solely on medication-guided narrowing |
| **Ambiguity handling** | If two candidates match equally and both are leaves, agent presents both; if both have children, prefers the one whose title better reflects the strongest clinical signal |

---

#### Mode 5 — `med-id` (Medication Identification)

**Tools:** `normalize_medical_term`, `get_containing_medications`, `get_hierarchies_for_containing_medications`

#### KG GraphQL Schemas

**`normalize_medical_term`** — REST only (no GraphQL). Called with `domain="Medication"`.

**`get_containing_medications`** — Step 1: Get dose forms and root-level containing medications for an ingredient-level medication.

```graphql
{
  lexical(code: "{imo_lexical_code}", domain: medication) {
    title
    code
    ... on MedicationLexical {
      domainNarrower(offset: {offset}, size: {SIZE}) {
        code
        title
      }
      containingMedications {
        code
        title
      }
    }
  }
}
```

> **Pagination:** `domainNarrower` uses `offset/size: 1000` with auto-fetch loop. `containingMedications` does NOT have offset/size — no pagination needed (returns all items in one call).

**`get_hierarchies_for_containing_medications`** — Batch tool: accepts comma-separated codes, internally calls `get_hierarchy_for_containing_medication` for each code. Returns 3-level nested `domainNarrower` hierarchy (strengths → dose forms → SCD/SBD names):

```graphql
{
  lexical(code: "{imo_lexical_code}", domain: medication) {
    code
    title
    ... on MedicationLexical {
      domainNarrower(offset: {offset}, size: {SIZE}) {
        code
        title
        ... on MedicationLexical {
          domainNarrower(offset: 0, size: {SIZE}) {
            code
            title
            ... on MedicationLexical {
              domainNarrower(offset: 0, size: {SIZE}) {
                code
                title
              }
            }
          }
        }
      }
    }
  }
}
```

> **Pagination:** Top-level `domainNarrower` is paginated with `offset/size: 1000`. Nested levels use `offset: 0, size: 1000` (single page — children per item are small).

#### Edge Cases

| Edge Case | Behavior |
|-----------|----------|
| **Single vs multiple substance** | Single substance (no "/" in name): use root `containingMedications` directly → batch hierarchy call. Multiple substance ("/" in name): iterate each `domainNarrower` code through `get_containing_medications` first, then batch all collected `containingMedications` codes |
| **Batch call pattern** | `get_hierarchies_for_containing_medications` must be called exactly ONCE with ALL codes — never call multiple times, never skip codes |
| **`containingMedications` not paginated** | Unlike `domainNarrower`, `containingMedications` has no offset/size in the KG schema — all items returned in a single response |
| **3-level hierarchy depth** | The nested query fetches exactly 3 levels of `domainNarrower` — deeper nesting would exceed KG depth limits |
| **Missing containing medications** | If a medication has no `containingMedications` (empty list), it may be at the leaf/SCD level already — no hierarchy call needed |

---

#### Mode 6 — `dx-to-med` (Diagnosis to Medication)

**Tools:** `normalize_medical_term`, `validate_medication_association`

#### KG GraphQL Schemas

**`normalize_medical_term`** — REST only (no GraphQL). Called with `domain="Problem"` for the diagnosis and `domain="Medication"` for each medication.

**`validate_medication_association`** — A wrapper tool that internally calls `get_treatments_for_problem` (same GraphQL as Mode 2), then performs exact code matching in Python.

**Underlying GraphQL — `associatedTreatments` (paginated):**

```graphql
query GetTreatments($code: String!, $domain: IMODomain!) {
  lexical(code: $code, domain: $domain) {
    code
    title
    ... on ProblemLexical {
      numberOfAssociatedTreatments
      numberOfSupportiveTreatments
      associatedTreatments(offset: {offset}, size: {SIZE}) {
        ... on Lexical { code title }
        ... on MedicationLexical { code title }
      }
    }
  }
}
```

**Underlying GraphQL — `supportiveTreatments` (paginated separately):**

```graphql
query GetTreatments($code: String!, $domain: IMODomain!) {
  lexical(code: $code, domain: $domain) {
    ... on ProblemLexical {
      supportiveTreatments(offset: {offset}, size: {SIZE}) { code title }
    }
  }
}
```

> **Pagination:** `associatedTreatments` and `supportiveTreatments` are paginated in separate query loops, each using `offset/size: 1000` with auto-fetch.

**Post-query matching logic (Python, not GraphQL):**
1. Fetch full `associatedTreatments` list for the diagnosis
2. Build a code→title lookup map from the KG results
3. Check each provided medication code against the map — exact code match
4. Return `matched` (medication code + KG title) and `unmatched_codes`

#### Edge Cases

| Edge Case | Behavior |
|-----------|----------|
| **Code-based validation, not text** | Medications are matched by exact IMO lexical code against KG `associatedTreatments` — text similarity is not used |
| **No medication codes provided** | If `medication_codes` is empty, returns the raw `get_treatments_for_problem` result without filtering |
| **Empty KG treatments** | If the diagnosis has no `associatedTreatments` in KG, all medications are reported as unmatched — agent does NOT infer associations from medical knowledge |
| **Dual pagination** | `associatedTreatments` and `supportiveTreatments` are fetched in separate pagination loops — each can have thousands of items |
| **Normalize failures** | If a medication fails to normalize, it is listed as "Could not normalize — skipped" and excluded from validation |

---

#### Mode 7 — `dx-infer-proc` (Diagnosis Specificity using Procedure)

**Tools:** `normalize_medical_term`, `find_diagnosis_by_procedure`

#### KG GraphQL Schemas

**`normalize_medical_term`** — REST only (no GraphQL). Called with `domain="Problem"` for the base diagnosis and `domain="Procedure"` for each procedure.

**`find_diagnosis_by_procedure`** — Two-phase tool: traverses the entire `domainNarrower` hierarchy under a base diagnosis, then checks each node's procedures for matches.

**Phase 1 — Hierarchy traversal (nested 3-level `domainNarrower` with ICD-10 mappings):**

```graphql
{
  lexical(code: "{code}", domain: problem) {
    code
    title
    ... on ProblemLexical {
      domainNarrower(size: {size}, offset: {offset}) {
        code
        title
        ... on ProblemLexical {
          numberOfDomainChildren
          mappings { code title codeSystem }
          domainNarrower(size: {size}, offset: 0) {
            code
            title
            ... on ProblemLexical {
              numberOfDomainChildren
              mappings { code title codeSystem }
              domainNarrower(size: {size}, offset: 0) {
                code
                title
                ... on ProblemLexical {
                  numberOfDomainChildren
                  mappings { code title codeSystem }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

> **Traversal:** BFS queue processes the tree in paginated 3-level batches (max depth: 5). Nodes with `numberOfDomainChildren > len(children)` are re-queued for deeper traversal. Collects all descendant codes and their ICD-10 mappings.

**Phase 2 — Procedure checking (concurrent, 20 threads):**

```graphql
{
  lexical(code: "{code}", domain: problem) {
    code
    title
    ... on ProblemLexical {
      treatmentProcedures { code title }
      evaluationProcedures { code title }
      preventiveProcedures { code title }
    }
  }
}
```

> **Concurrency:** Phase 2 runs with `ThreadPoolExecutor(max_workers=20)` — checks all collected codes in parallel. Only nodes where at least one procedure code matches are returned as `matched_nodes`.

**Procedure categories:** Each matched procedure includes a `category` field: `treatment`, `evaluation`, or `preventive`.

#### Edge Cases

| Edge Case | Behavior |
|-----------|----------|
| **Full hierarchy traversal** | Unlike Mode 4 (iterative drill-down), this tool traverses the ENTIRE tree under the base diagnosis — not just one path. Returns ALL matching descendants |
| **Three procedure types** | Checks `treatmentProcedures`, `evaluationProcedures`, AND `preventiveProcedures` — a procedure can match in any category |
| **Multiple matches** | When multiple descendant diagnoses match the same procedure, agent selects the best fit based on clinical note context (site, laterality, chronicity, etc.) |
| **No matches** | If no descendant has the given procedure in its KG edges, agent reports "procedure could not be linked to any narrower diagnosis" |
| **Max depth 5** | Hierarchy traversal stops at depth 5 — covers nearly all KG hierarchies |
| **Verbatim procedure extraction** | Procedures must be extracted EXACTLY as written in the clinical note — including parenthetical qualifiers like `(number/volume)` — to normalize to the correct IMO code |
| **ICD-10 mappings included** | Phase 1 collects `mappings` with `codeSystem: "icd10cm"` for each node — available in matched results without extra queries |

---

#### Mode 8 — `procedure_inference` (Diagnosis Specificity using Procedure with Temporality)

**Tools:** `normalize_medical_term`, `find_temporal_diagnoses`

#### KG GraphQL Schemas

**`normalize_medical_term`** — REST only (no GraphQL). Called with `domain="Procedure"` for the procedure.

**`find_temporal_diagnoses`** — Queries `ProcedureLexical.associatedProblems` to get ALL associated Problem concepts for a procedure, including temporal variants ("status post", "history of"), complications, and approach-specific diagnoses.

```graphql
{
  lexical(code: "{procedure_code}", domain: procedure) {
    code
    title
    ... on ProcedureLexical {
      numberOfAssociatedProblems
      associatedProblems(offset: {offset}, size: {SIZE}) {
        code
        title
        ... on ProblemLexical {
          mappings { code codeSystem }
        }
      }
    }
  }
}
```

> **Pagination:** `associatedProblems` uses `offset/size: 1000` with auto-fetch loop until `len(page) < SIZE`.

> **Post-processing:** Filters each problem's `mappings` for `codeSystem == "icd10cm"`, returns `problems_with_icd10` list with `{ code, title, icd10_codes }`.

#### Edge Cases

| Edge Case | Behavior |
|-----------|----------|
| **Temporal selection** | Agent selects from associated problems based on timing: "status post" for recent procedures (~<1 year), "history of" for remote procedures (>1 year) |
| **Approach-specific variants** | If clinical note specifies surgical approach (e.g., "laparoscopic"), agent prefers approach-specific variant (e.g., "status post laparoscopic cholecystectomy") |
| **Complications** | If the note mentions procedure-related complications, agent selects the matching complication concept (e.g., "retained gallstones following cholecystectomy") |
| **Strict scoping** | Agent MUST ignore unrelated clinical content (labs, medications, symptoms, imaging) — only procedure name, timing, surgical approach, and procedure-related complications influence the temporal diagnosis |
| **Ambiguous timing** | If timing is unclear, agent presents top candidates and explains the clinical distinction between "status post" vs "history of" |
| **ICD-10 included** | Each associated problem includes ICD-10-CM mappings directly from KG `mappings` — no extra normalization needed |

---

#### Mode 9 — `lab-id` (Lab Identification — Prototype)

**Tools:** `normalize_medical_term`, `identify_lab`

#### KG GraphQL Schemas

**`normalize_medical_term`** — REST only (no GraphQL). Called with `domain="Lab"`. Supports optional `order_name` parameter for panel context (e.g., `order_name="comprehensive metabolic panel"` when normalizing a component like "glucose").

**`identify_lab`** — Queries the KG for a lab's narrower concepts and LOINC code mappings. Note: labs are stored under the **Procedure domain** in the KG, so the GraphQL uses `domain: procedure` despite the Normalize call using `domain="Lab"`.

```graphql
{
  lexical(code: "{lab_code}", domain: procedure) {
    code
    title
    ... on ProcedureLexical {
      mappings { code codeSystem }
      domainNarrower {
        code
        title
        ... on ProcedureLexical {
          mappings { code codeSystem }
        }
      }
    }
  }
}
```

> **No pagination:** `domainNarrower` does NOT use `offset/size` — all narrower concepts returned in a single query.

> **Post-processing:** Filters `mappings` for `codeSystem == "loinc"` at both root level and each narrower concept. Returns `{ lab, loinc_codes, narrower_concepts }` where each narrower concept includes its own `loinc_codes`.

#### Edge Cases

| Edge Case | Behavior |
|-----------|----------|
| **Domain mismatch** | Normalize uses `domain="Lab"` but KG GraphQL uses `domain: procedure` — labs are stored under the Procedure domain in the KG schema |
| **ORDER vs COMPONENT classification** | Labs must be classified before normalization: ORDER (panel) passes panel name as `input_term`; COMPONENT (single analyte) passes analyte name as `input_term` with optional `order_name` for panel context |
| **`order_name` parameter** | When a component belongs to a known panel, passing the panel name as `order_name` improves normalization accuracy (e.g., `input_term="glucose", order_name="comprehensive metabolic panel"`) |
| **No pagination on `domainNarrower`** | Unlike other modes, this query fetches all narrower concepts in one call — no offset/size loop needed |
| **LOINC filtering** | Only mappings with `codeSystem == "loinc"` are extracted — other code systems in `mappings` are ignored |
| **Prototype status** | This mode is a prototype — the KG lab hierarchy may have limited depth compared to Problem or Medication domains |

### Three Core Patterns

Most scenarios fall into one of three patterns:

#### Pattern A: Iterative Drill-Down (scenarios 4, 7)

The simplest pattern. Normalize inputs → call a `domainNarrowerBy*` edge repeatedly → stop at the leaf.

```
normalize(diagnosis) → normalize(medication/procedure)
  → get_*_diagnosis_proto(diagnosis_code, [med/proc_codes])
  → pick best match → drill deeper (if numberOfDomainChildren > 0)
  → repeat until leaf or no further matches
```

**Key tool:** `get_medication_diagnosis_proto` or `get_procedure_diagnosis_proto`

**When to use this pattern:** When you have a base diagnosis + a single clinical signal (one medication or one procedure) and want to find the most specific subtype.

#### Pattern B: Two-Phase Refinement (scenarios 1, 2)

Phase 1 narrows via a primary signal (clinical note or medication). Phase 2 applies remaining refinement axes (type, laterality, severity) one at a time.

```
Phase 1: normalize → drill down via primary signal (note-driven or med-driven)
Phase 2: get_allowed_refinements → match to clinical evidence → get_narrower_sequential_refinements
```

**Key insight:** Phase 2 uses `refinementNarrower` with `allowedRefinements` groups — the most complex KG pattern (see [Section 7](#7-handling-the-narrower-sequential-refinements)). The `refine` mode (scenario 2) combines *both* medication drill-down and refinement in a single agent, requiring 9 tools.

#### Pattern C: Relationship Lookup (scenarios 3, 5, 6)

Query KG relationship edges to get associated entities (treatments, containing medications, treated problems), then process/score the results.

```
normalize(input) → query KG relationship edge → process/filter/score results
```

**Key tools vary:** `get_treatments_for_problem`, `get_containing_medications`, `get_lexical_for_ranking`

**When to use this pattern:** When the goal is to *retrieve* related concepts rather than *narrow* a diagnosis.

### Building a New Scenario

To add a new inference scenario:

1. **Identify the KG edge** — what relationship in the Knowledge Graph connects your inputs to the desired output?
2. **Pick the pattern** — drill-down (A), two-phase refinement (B), or relationship lookup (C)?
3. **Build the API client methods** — one method per KG query, with pagination support
4. **Write the `@tool` functions** — thin wrappers that call the API client and return JSON strings
5. **Write the system prompt** — tell the LLM what the scenario does, when to call each tool, and how to present results
6. **Choose the normalize domain** — `"Problem"` for diagnoses, `"Medication"` for drugs, `"Procedure"` for procedures, `"Lab"` for labs

### Normalize Domain Reference

| Scenario | Mode | Input 1 Domain | Input 2 Domain |
|----------|------|---------------|----------------|
| Diagnosis Specificity using Problems | `ds-conditions` | Problem | — (uses clinical note text) |
| Refine Diagnosis using Medication | `refine` | Problem | Medication |
| Rank Diagnosis using Medication | `rank` | Problem (candidates) | Medication |
| Diagnosis Specificity using Medication | `dx-infer` | Problem | Medication |
| Medication Identification | `med-id` | Medication | — |
| Diagnosis to Medication | `dx-to-med` | Problem | — |
| Diagnosis Specificity using Procedure | `dx-infer-proc` | Problem | Procedure |
| DS using Procedure with Temporality | `procedure_inference` | Problem | Procedure |
| Lab Identification (Prototype) | `lab-id` | Lab | — |

---

## 2. Agent Design

### Use the ReAct Pattern

This agent uses the **ReAct** (Reason + Act) pattern:
1. The LLM **reads** the user's question
2. It **thinks** about what to do (which tool to call)
3. It **acts** (calls a tool)
4. It **observes** the result
5. It **repeats** steps 2-4 until it has enough information
6. It **responds** to the user

This is handled automatically by LangGraph's `create_react_agent`.

### Keep Tools Simple and Focused

Each tool should do **one thing well**:

| Tool | Does | Does NOT |
|------|------|----------|
| `normalize_medical_term` | Converts text to a code | Look up refinements |
| `get_lexical` | Returns refinements for a code | Apply refinements |
| `get_narrower_sequential_refinements` | Applies refinements to find a specific concept | List all available refinements |

**Why?** The LLM decides which tool to use based on its docstring. If a tool does too many things, the LLM gets confused about when to use it.

### Let the LLM Decide the Workflow

Don't hardcode the order of API calls. The LLM should figure out the right sequence based on the user's question. For example:
- "Find refinements for diabetes" → normalize → get_lexical
- "Apply type 2 to diabetes" → might skip normalize if it already has the code from a previous turn

The system prompt gives guidelines, but the LLM has flexibility.

### The Agent Remembers; the KG API Does Not

The agent maintains **conversation state within a session** — messages are carried across turns so users can ask follow-up questions naturally (see [Conversation Management](#10-conversation-management)).

The **KG API has no memory between calls** — each API request is fully independent. The agent is responsible for carrying relevant context (codes, refinements) from one call to the next.

---

## 3. System Prompt Writing

### Be Explicit About What to Do AND What NOT to Do

Good rules are specific and actionable:

```
GOOD: "ALWAYS use default_lexical_code from normalize results for KG lookups, NOT lexical_code"
BAD:  "Use the right code for lookups"
```

### Tell the LLM About Response Format

If you want the answer in a specific format, show an example in the prompt:

```
Present the refinements like this:

**Base Concept:** Diabetes mellitus — Lexical Code: 29688 — ICD-10: E11
**IMO KG Link:** https://studio.imohealth.com/#/terminology-browser/graph?id=29688

| Refinement Group | Available Options |
|---|---|
| Type | type 1 (231), type 2 (230) |
```

### Include "Never" Rules for Common Mistakes

LLMs tend to:
- Make up ICD-10 codes → "NEVER fabricate ICD-10 codes — always get them from tool results"
- Answer from memory → "ALWAYS call tools for EVERY question. Never answer from cached results"
- Dump raw JSON → "Present results in a clear, readable format — do NOT dump raw JSON"

### Tell the LLM About Tool Behavior

If a tool has special behavior (like automatic batching), explain it in the prompt so the LLM doesn't try to work around it:

```
Pass ALL selected refinements in a SINGLE call. The backend automatically handles
GraphQL depth limits by chunking internally.
```

Without this, the LLM might try to split calls manually — causing confusion and duplicate work.

### Keep the Prompt Focused

This agent answers **questions about medical terms**. The prompt says clearly:
- What it IS: "You are an IMO Diagnosis Specificity Q&A Agent"
- What it does: "answers questions about medical term refinements"
- What it does NOT do: the agent does not request Personal Health Information (PHI) or patient identifiers — it can accept EHR clinical notes (e.g., ED discharge notes, encounter notes) as context, but does not require them

---

## 4. Tool Design

### Docstrings Are Critical

The LLM reads tool docstrings to decide:
1. **Whether** to use the tool
2. **What arguments** to pass
3. **What to expect** in the response

Write docstrings like you're explaining to a smart person who has never seen your codebase:

```python
@tool
def get_narrower_sequential_refinements(
    imo_lexical_code: str,
    refinement_sequence: List[List[str]],
    include_mappings: bool = True,
    domain: str = "Problem",
) -> str:
    """Resolve the most specific concept by applying refinements sequentially.
    Pass ALL refinements in one call — the backend handles depth limits automatically.

    Args:
        imo_lexical_code: Base concept lexical code to start from
        refinement_sequence: Array of arrays - each inner array contains one refinement code.
            Example: [["6845"], ["2187"], ["2126"], ["2316"]]
        include_mappings: Set to true to include ICD-10 code mappings in the response
        domain: The clinical domain. Use "Problem" for diagnoses/conditions.
    """
```

### Always Include Examples in Arg Descriptions

Notice `Example: [["6845"], ["2187"], ["2126"], ["2316"]]` in the docstring above. Without this, the LLM might format the argument incorrectly (e.g., `["6845", "2187"]` instead of `[["6845"], ["2187"]]`).

### Return JSON Strings from Tools

Tools must return strings (LangChain requirement). Always use `json.dumps(result, indent=2)`:

```python
result = _kg_client.normalize_medical_term(input_term, domain)
return json.dumps(result, indent=2)
```

**Why `indent=2`?** Makes it easier for the LLM to read the structure. Flat JSON is harder for LLMs to parse correctly.

### Use Consistent Response Shapes

Every tool response should have at least:
- `success: true/false` — did it work?
- The actual data (or `error` message if it failed)

This lets the LLM know immediately whether the tool call worked.

### Handle Backend Complexity in the Tool, Not the Prompt

The GraphQL depth limit is a **backend concern**. We handle it in `api_client.py`, not by asking the LLM to split calls. This is better because:
- The LLM makes fewer calls (faster response)
- No risk of the LLM splitting incorrectly
- Simpler system prompt
- Works even if the LLM ignores the instruction

---

## 5. API Client & Authentication

### Cache Tokens with Expiry

OAuth tokens have a long lifetime (configured in Auth0 — currently up to 24 hours). The auth response includes an `expires_in` field (seconds) — use that directly rather than hardcoding a duration, so the cache stays correct if the token lifetime ever changes:

```python
def _get_normalize_token(self):
    if self._normalize_token and time.time() < self._normalize_token_expiry:
        return self._normalize_token  # still valid
    token, expires_in = self._get_oauth_token(client_id, client_secret)
    if token:
        self._normalize_token = token
        self._normalize_token_expiry = time.time() + expires_in - 300  # 5-min buffer
    return token
```

**Why subtract 5 minutes?** A small buffer prevents edge cases where the token expires between checking and using it.

### Token Caching Is Handled Automatically

A single set of client credentials is used for both the Normalize API and the Knowledge Graph API. Token acquisition and caching are handled internally — you configure credentials once and the client manages the rest.

### Always Set Timeouts

Every HTTP request must have a timeout:

```python
response = requests.post(url, json=payload, timeout=30)
```

Without this, a hung API could block your server forever.

### Use a Single Client Instance

Create one `KGApiClient()` at module level. This ensures token caching works across all requests:

```python
# agent.py
_kg_client = KGApiClient()  # single instance, reused
```

Don't create a new client per request — you'd lose the cached tokens.

---

## 6. GraphQL Query Construction

### Use Variables, Not String Interpolation

Always pass values through GraphQL variables:

```python
# GOOD — safe, no injection risk
query = """query GetLexical($code: String!, $domain: IMODomain!) {
  lexical(code: $code, domain: $domain) { ... }
}"""
variables = {"code": "29688", "domain": "problem"}

# BAD — injection risk, breaks on special characters
query = f"""query {{ lexical(code: "{code}", domain: "{domain}") {{ ... }} }}"""
```

### Keep Queries Lean

Only request the fields you need. The Knowledge Graph can return massive responses for broad terms.

**Why `get_lexical` doesn't include `domainNarrower`:** A term like "diabetes" has hundreds of child concepts. Including all of them would produce 200,000+ characters — far too much for the LLM's context window. Instead, we have a separate tool (`get_narrower_sequential_refinements`) that fetches only the specific path the user wants.

### Use Type-Specific Fragments

The Knowledge Graph uses GraphQL interfaces. `ProblemLexical` has fields that other types don't. Use inline fragments:

```graphql
... on ProblemLexical {
  allowedRefinements(offset: 0, size: 1000) { code title group { code title } }
}
```

This prevents errors when querying non-Problem concepts.

### Understand the Depth Limit

The GOAT GraphQL API has a **maximum query depth of 7**. Here's how depth is counted:

- Only **non-scalar selection sets** count toward depth (scalar fields like `code`, `title` do not add depth).
- Inline fragments (`... on ProblemLexical`) do **not** add depth.

The production query includes `allowedRefinements { group { code title } }` inside each level. This adds 2 extra depth levels per `refinementNarrower`. With 3 levels of nesting, `group` lands exactly at depth 7:

```graphql
query {                                              # depth 1
  lexical(code: ...) {                               # depth 2
    ... on ProblemLexical {                          # no extra depth — inline fragment
      refinementNarrower(refinements: $ref0) {       # depth 3
        ... on ProblemLexical {
          appliedRefinements { code title }          # depth 4
          allowedRefinements {                       # depth 4
            group { code title }                     # depth 5
          }
          refinementNarrower(refinements: $ref1) {   # depth 4
            ... on ProblemLexical {
              appliedRefinements { code title }      # depth 5
              allowedRefinements {                   # depth 5
                group { code title }                 # depth 6
              }
              refinementNarrower(refinements: $ref2) { # depth 5
                ... on ProblemLexical {
                  appliedRefinements { code title }  # depth 6
                  allowedRefinements {               # depth 6
                    group { code title }             # depth 7  ← AT LIMIT
                  }
                  mappings { code title ... }        # depth 6
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**Rule: Maximum 3 nested `refinementNarrower` levels per query.** A 4th level would push `allowedRefinements.group` to depth 8 — which the API rejects with HTTP 400.

---

## 7. Handling the Narrower Sequential Refinements

This is the most complex part of the system. Here's how it works and why.

### The Problem

Users may want to apply 4, 5, or more refinements to a concept. But the GraphQL API only allows 3 levels of nesting per query. We need a way to apply unlimited refinements while staying within the depth limit.

### The Solution: Automatic Batching + Chaining + Pagination

The `get_narrower_sequential_refinements` method in `api_client.py`:

1. **Takes all refinements** in one call (e.g., `["6845", "2187", "2126", "2316"]`)
2. **Splits into batches of 3** → `["6845", "2187", "2126"]` and `["2316"]`
3. **Executes batch 1** with the original base code → gets deepest resolved code
4. **Executes batch 2** using the result from batch 1 as the new base
5. **Repeats** until all batches are done or a batch finds no deeper concept
6. **Paginates** the deepest `refinementNarrower` result — each query requests `size: 1000`; if exactly 1000 items come back, additional pages are fetched automatically until exhausted
7. **Paginates `allowedRefinements`** for each item in the final result the same way

### Building Nested Queries Dynamically

For 3 refinements, the query looks like:

```graphql
query GetRefinedNarrowerSequential($code: String!, $domain: IMODomain!, $ref0: [String!], $ref1: [String!], $ref2: [String!]) {
  lexical(code: $code, domain: $domain) {
    code
    title
    ... on ProblemLexical {
      refinementNarrower(refinements: $ref0, offset: 0, size: 1000) {
        code
        title
        ... on ProblemLexical {
          appliedRefinements { code title }
          refinementNarrower(refinements: $ref1, offset: 0, size: 1000) {
            code
            title
            ... on ProblemLexical {
              appliedRefinements { code title }
              refinementNarrower(refinements: $ref2, offset: 0, size: 1000) {
                code
                title
                ... on ProblemLexical {
                  appliedRefinements { code title }
                  allowedRefinements(offset: 0, size: 1000) { code title group { code title } }
                  mappings { code title codeSystem relationshipType }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

The code builds this from **inside out**:
1. Start with the innermost level (last refinement)
2. Wrap it with the next outer level
3. Repeat until all levels are built

```python
# Start with innermost
nested = f"... on ProblemLexical {{ refinementNarrower(refinements: $ref2) {{ {fields} }} }}"

# Wrap with next level
nested = f"... on ProblemLexical {{ refinementNarrower(refinements: $ref1) {{ {fields} {nested} }} }}"

# Wrap with outermost
nested = f"... on ProblemLexical {{ refinementNarrower(refinements: $ref0) {{ {fields} {nested} }} }}"
```

### Walking the Response Tree

After the query returns, we need to find the deepest resolved concept. The response is nested:

```json
{
  "code": "41696",
  "title": "Depression",
  "refinementNarrower": [{
    "code": "15155",
    "title": "major depressive disorder",
    "appliedRefinements": [{"code": "6845", "title": "major depressive disorder"}],
    "refinementNarrower": [{
      "code": "65860571",
      "title": "major depressive disorder with single episode",
      "appliedRefinements": [{"code": "2187", "title": "single episode"}],
      "refinementNarrower": [{
        "code": "1493378180",
        "title": "current episode of major depressive disorder without prior episode",
        "appliedRefinements": [{"code": "2126", "title": "currently active"}],
        "allowedRefinements": [...],
        "mappings": [...]  ← this is the deepest
      }]
    }]
  }]
}
```

Note: this is the raw `lexical` object from the GraphQL response, not the final tool output. The `_extract_deepest_narrower` method walks this tree:

```python
def _extract_deepest_narrower(self, lexical: Dict, num_steps: int) -> List[Dict]:
    """Traverse nested refinementNarrower response to get the deepest results."""
    current_list = lexical.get("refinementNarrower", [])
    for _ in range(num_steps - 1):
        if not current_list:
            break
        current_list = current_list[0].get("refinementNarrower", [])
    return current_list
```

### Handling Partial Resolution

Sometimes the graph doesn't have a concept for all refinements. For example:
- "Depression" + "major depressive" + "single episode" + "currently active" → resolves to code 1493378180
- But adding "with psychotic features" → no further concept exists

In this case, the API returns `refinementNarrower: []` (empty) with the original base concept code. The LLM reads the empty `refinementNarrower` and understands that no narrower concept was found for those refinements — it reports the deepest concept it reached in the previous successful batch.

This prevents the LLM from thinking the entire call failed.

### Refinement Ordering Matters

Refinements should be ordered by clinical hierarchy:
1. **Type** (e.g., "major depressive disorder")
2. **Complication** (e.g., "with peripheral neuropathy")
3. **Laterality** (e.g., "right", "left", "bilateral")
4. **Severity** (e.g., "mild", "moderate", "severe")
5. **Other qualifiers** (e.g., "currently active", "in remission")

The system prompt tells the LLM to follow this order. Different orderings may produce different results (or no results) because the graph structure follows this hierarchy.

---

## 8. Streaming & Real-Time UI

### Why Stream?

The agent takes 5-15 seconds to fully respond (multiple API calls + LLM thinking). Without streaming, the user stares at a blank screen. With streaming, they see:
1. "Calling normalize API..." (immediate feedback)
2. API results appearing
3. The answer being typed word by word

### Use Server-Sent Events (SSE)

SSE is simpler than WebSockets for one-way server-to-client streaming:

```python
# Server side
def generate():
    for event in stream(message, session_id):
        yield f"data: {json.dumps(event)}\n\n"

return Response(generate(), mimetype="text/event-stream")
```

```javascript
// Browser side
const reader = response.body.getReader();
// read chunks, parse "data: {...}\n\n" lines
```

### Event Types

Define clear event types so the UI knows what to render:

| Event type | Meaning | UI action |
|-----------|---------|-----------|
| `tool_use` | Agent is about to call a tool | Show loading indicator |
| `tool_use_complete` | Tool call details are ready | Show tool name + arguments |
| `tool_result` | Tool returned data | Show collapsible result |
| `text_chunk` | One word/phrase of the answer | Append to answer area |
| `text` | Full text block finished | Finalize text rendering |
| `done` | Agent finished | Hide loading, enable input |
| `error` | Something failed | Show error message |

### Disable Response Buffering

Add these headers to prevent proxies (nginx, AWS ALB) from buffering your stream:

```python
headers={
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",  # nginx
    "Connection": "keep-alive",
}
```

---

## 9. Error Handling

### Validate Credentials at Startup

Check credentials early, before the user sends a message:

```python
if not config.IMO_NORMALIZE_CLIENT_ID or not config.IMO_NORMALIZE_CLIENT_SECRET:
    yield {"type": "error", "error": "Normalize API credentials not configured."}
    return
```

### Handle Token Failures Gracefully

If OAuth token fetch fails, return a clear error — don't let a `None` token cause a confusing 401 later:

```python
def _get_normalize_token(self):
    token = self._get_oauth_token(...)
    if not token:
        return None  # caller checks this

# In the API method:
token = self._get_normalize_token()
if not token:
    return {"success": False, "error": "Failed to obtain API token"}
```

### Return Structured Errors from Tools

Every tool response uses `"success": true/false`. On failure, include an `error` field with a human-readable message:

```python
return {"success": False, "error": "Normalize API error: 401 - Invalid credentials"}
```

The LLM reads this and can explain the issue to the user.

### Log Everything Server-Side

Print tool calls and results to the console. This is invaluable for debugging:

```python
print(f"  [TOOL REQUEST] {tool_name}: {json.dumps(args)}")
print(f"  [TOOL RESULT] {tool_name}: {json.dumps(data)[:500]}")
```

### Catch Exceptions at the Top Level

Wrap the entire agent loop in try/except so unhandled errors become user-visible error messages:

```python
try:
    async for event in agent.astream_events(...):
        ...
except Exception as e:
    yield {"type": "error", "error": f"Agent execution failed: {str(e)}"}
```

---

## 10. Conversation Management

### Store Messages Per Session

Each browser tab gets a unique session ID. Store messages by session:

```python
_conversations: Dict[str, List[Dict[str, str]]] = {}
```

After each exchange, append both the user message and assistant response.

### Enable Multi-Turn Follow-Ups

Because we store conversation history, users can say:
- Turn 1: "Find refinements for diabetes"
- Turn 2: "Now apply type 2 to that"

The LLM sees the full history and knows "that" refers to diabetes from the previous turn.

### Provide a Reset Mechanism

Always give users a way to clear conversation history:

```python
@app.route('/api/reset', methods=['POST'])
def reset_conversation():
    agent.reset_session(session_id)
    session['session_id'] = str(uuid.uuid4())  # new session
```

### Don't Store Indefinitely

In production, add TTL (time-to-live) or max conversation length to prevent memory leaks. For this demo, in-memory storage is fine.

---

## 11. Security

### Never Hardcode Credentials

```python
# GOOD
client_id = os.getenv("IMO_NORMALIZE_CLIENT_ID")

# BAD
client_id = "abc123-secret-key"
```

### Use Environment Variables or Secret Stores

Priority order for resolving credentials:
1. AWS SSM Parameter Store (production)
2. Environment variables (local development)
3. `.env` file (developer convenience — via python-dotenv)

### Never Expose Tokens to the Browser

OAuth tokens stay server-side only. The browser never sees them — it only sends messages and receives events.

### Use HTTPS for All API Calls

All IMO API endpoints use HTTPS. Never downgrade to HTTP, even in development.

### Set a Real Flask Secret Key in Production

```python
# Development (random per restart — fine for dev)
app.secret_key = os.urandom(24)

# Production (persistent, strong secret)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
```

### Sanitize User Input

The user's message goes into the LLM prompt. While LangGraph handles this safely, be aware of:
- Very long messages (could hit token limits)
- Prompt injection attempts (the system prompt's rules help mitigate this)

---

## 12. Testing & Debugging

### Test Each Layer Independently

1. **API Client alone:** Call `_kg_client.normalize_medical_term("diabetes")` directly in a Python shell
2. **Tools alone:** Call the `@tool` functions with known inputs
3. **Agent:** Send messages through the full agent
4. **Full stack:** Use the browser UI

### Common Debug Queries

These are good test cases that exercise different paths across the scenarios:

**Problem-based (ds-conditions):**

| Query | Tests |
|-------|-------|
| "Find refinements for diabetes" | normalize → get_lexical |
| "Get narrower for fever" | normalize → get_lexical (simple concept) |
| "Apply type 2 to diabetes" | normalize → get_narrower (follow-up from previous) |
| "Refine depression → major depressive → single episode → currently active" | 3 refinements (single batch) |
| "Refine depression → major depressive → single episode → currently active → with psychotic features" | 4+ refinements (multi-batch + partial resolution) |

**Medication-based (dx-infer, refine, rank, dx-to-med, med-id):**

| Query | Scenario | Tests |
|-------|----------|-------|
| "Diabetes mellitus + Metformin" | dx-infer | normalize(Problem) + normalize(Medication) → get_medication_diagnosis_proto |
| "Diabetes + Metformin" (with clinical note) | refine | Phase 1 med drill-down → Phase 2 refinement axes |
| "Rank: paroxysmal AFib, ventricular tachycardia vs Digoxin + Warfarin" | rank | normalize meds → get_lexical_for_ranking → scoring |
| "Treatments for type 2 diabetes mellitus" | dx-to-med | normalize(Problem) → get_treatments_for_problem (pagination) |
| "Identify Metformin" | med-id | normalize(Medication) → get_containing_medications → get_hierarchy_for_containing_medication |

**Procedure-based (dx-infer-proc, procedure_inference):**

| Query | Scenario | Tests |
|-------|----------|-------|
| "Tonsillitis + Tonsillectomy" | dx-infer-proc | normalize(Problem) + normalize(Procedure) → get_procedure_diagnosis_proto |
| "Coronary artery disease + CABG (pre-operative)" | procedure_inference | Same as above + temporal context |

**Lab-based (lab-id):**

| Query | Tests |
|-------|-------|
| "Hemoglobin A1c" | normalize(Lab) → KG hierarchy exploration |

### Check the Console Logs

Every tool call and result is logged. Look for:
- `[TOOL REQUEST]` — what the LLM asked for
- `[TOOL RESULT]` — what the API returned
- Error messages with `✗` or `⚠`

### Verify the GraphQL Query

To debug query issues, print the generated query:

```python
# In _execute_narrower_batch, temporarily add:
print(f"  [QUERY] {query}")
print(f"  [VARS] {json.dumps(variables)}")
```

### Test Token Refresh

Force a token expiry to ensure refresh works:

```python
_kg_client._normalize_token_expiry = 0  # force refresh on next call
```

---

## 13. Performance

### Minimize LLM Round-Trips

Each LLM call adds 1-3 seconds of latency. Design tools so the LLM needs as few calls as possible:
- `get_lexical` returns ALL refinement groups in one call (not one-per-group)
- `get_narrower_sequential_refinements` accepts ALL refinements at once (backend batches internally)

### Use `temperature=0`

For deterministic, consistent results. Also slightly faster because the model doesn't need to sample multiple paths.

### Set `recursion_limit`

Prevent infinite tool-call loops:

```python
config={"recursion_limit": 50}
```

This means the agent can make at most 50 tool calls per request. More than enough for normal use, but prevents runaway loops if the LLM gets confused.

### Keep Token Usage Low

The `get_lexical` query is intentionally lean — no `domainNarrower`, no `synonyms`, no `refinementFamilies`. This keeps responses under ~2000 tokens even for broad terms.

If you add more fields to GraphQL queries, always test with broad terms like "diabetes" or "pain" to check response sizes.

---

## 14. Common Mistakes to Avoid

### Mistake: Using `lexical_code` Instead of `default_lexical_code`

The normalize API returns both. **Always use `default_lexical_code`** for Knowledge Graph lookups. The `lexical_code` might be an alias that the KG doesn't recognize.

### Mistake: Passing All Refinement Codes in a Flat Array

```python
# WRONG — the LLM might try this format
refinement_sequence = ["6845", "2187", "2126"]

# CORRECT — must be array of arrays
refinement_sequence = [["6845"], ["2187"], ["2126"]]
```

Each inner array represents one step in the traversal. The tool docstring shows the correct format.

### Mistake: Including `domainNarrower` in `get_lexical`

Adding `domainNarrower { ... }` to the `get_lexical` query would return ALL child concepts in the hierarchy. For "diabetes" this is 200,000+ characters. The LLM's context window would overflow and the response would be useless.

### Mistake: Not Handling Empty `refinementNarrower` Arrays

When the graph has no narrower concept for a refinement, it returns an empty `refinementNarrower: []`. Your code must check for this and stop chaining — don't pass an empty code to the next batch.

### Mistake: Creating a New `KGApiClient` Per Request

```python
# WRONG — token cache is lost every request
async def stream(message, session_id):
    client = KGApiClient()  # new client each time!
    ...

# CORRECT — single instance, tokens persist
_kg_client = KGApiClient()

async def stream(message, session_id):
    # uses _kg_client (module-level singleton)
    ...
```

### Mistake: Forgetting to Handle Partial Resolution

If 3 out of 4 refinements resolve but the 4th doesn't, the API returns `refinementNarrower: []` with the original base code. The LLM must interpret this as a partial success: it should report the best concept reached in the previous batch rather than saying "nothing was found". Teach the LLM this in the system prompt — the `refinementNarrower` being empty does not mean all refinements failed.

### Mistake: Asking the LLM to Handle API Limitations

```
# BAD system prompt:
"Due to depth limits, pass a MAXIMUM of 3 refinements per call. If you have more, chain multiple calls..."

# GOOD system prompt:
"Pass ALL refinements in a SINGLE call. The backend handles depth limits automatically."
```

LLMs often ignore complex instructions about API limitations. Handle limits in your code, not in the prompt.

### Mistake: Not Setting Timeouts on HTTP Requests

```python
# BAD — can hang forever
response = requests.post(url, json=payload)

# GOOD — fails after 30 seconds
response = requests.post(url, json=payload, timeout=30)
```

### Mistake: Dumping Raw JSON to the User

The LLM should present results in a human-readable format. The system prompt must explicitly say:
```
"Present results in a clear, readable format — do NOT dump raw JSON to the user."
```

Without this rule, LLMs frequently paste the raw API response.

---

## Quick Reference: Checklist for Adding a New Tool

When you need to add a new tool to an existing agent or build a new scenario:

- [ ] Identify which KG edge to traverse and which pattern to follow (see [Section 1](#1-inference-scenario-patterns))
- [ ] Create the API method in `kg_api_client.py` (handles auth, HTTP call, pagination, error handling)
- [ ] Create the `@tool` function (calls the API method, returns `json.dumps(result, indent=2)`)
- [ ] Write a clear docstring with: what it does, all args with types, an example
- [ ] Add the tool to the tools list passed to `create_react_agent`
- [ ] Write or update the system prompt to tell the LLM when/how to use it
- [ ] Set the correct normalize domain (`"Problem"`, `"Medication"`, `"Procedure"`, `"Lab"`)
- [ ] For notebook scenarios: add a display name in the `AGENT_CSS` tool-name mapping
- [ ] Test with a real query that should trigger the new tool
- [ ] Check that the LLM actually uses it (look at console logs)
- [ ] Verify response size is reasonable (under 5000 characters ideally)

---

## Quick Reference: Checklist for Modifying a GraphQL Query

- [ ] Check the GOAT GraphQL schema for available fields
- [ ] Keep total query depth under 7
- [ ] Use variables for all user-provided values (never interpolate directly)
- [ ] Use `... on ProblemLexical { }` for Problem-specific fields
- [ ] Test with broad terms (diabetes, pain, hypertension) to check response size
- [ ] Test with narrow terms (specific codes) to verify correct structure
- [ ] If adding nesting, count the depth carefully
- [ ] Update the `_extract_deepest_narrower` method if the response structure changes
