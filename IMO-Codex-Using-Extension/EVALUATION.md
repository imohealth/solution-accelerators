# IMO Health Plugin — Evaluation Test Set

Use this test set to validate the plugin after installation. Record results for each test case.

---

## Phase 1: MCP Server Connection

### 1.1 Inspect with MCP Inspector

```bash
npx @modelcontextprotocol/inspector@latest
```

- Enter URL: `https://api.imohealth.com/mcp`
- Verify: 15 tools discovered
- Verify: tool names, descriptions, and JSON schemas present
- Verify: authentication flow completes

### 1.2 Register in ChatGPT

1. Go to [ChatGPT Plugins](https://chatgpt.com/plugins)
2. Click **+** → **Add custom MCP server**
3. Name: `IMO Health MCP Gateway`
4. URL: `https://api.imohealth.com/mcp`
5. Configure OAuth credentials
6. Select **Create as a plugin**
7. Copy the `plugin_asdk_app_...` ID from the browser URL
8. Update `.app.json` with that ID

### 1.3 Tool Discovery Check

| Check | Expected | Pass? |
|---|---|---|
| Tools listed | 15 tools | |
| CCP NLP tools | 1 (entity_extraction) | |
| Core Search tools | 3 (search, detail, lookup) | |
| Normalize PPML tools | 1 (normalize_ppml_term) | |
| Categorize tools | 1 (categorize_problems) | |
| Knowledge Graph tools | 9 (get_lexical, get_mappings, get_narrower_hierarchy, get_narrower_sequential_refinements, get_narrower_with_refinements, get_allowed_refinements, get_cross_domain, get_refinement_group, get_related_problems) | |

---

## Phase 2: Tool Selection Evaluation

### 2.1 Direct Requests (should call specific tools)

| # | Prompt | Expected Tool(s) | Actual Tool(s) | Result |
|---|---|---|---|---|
| 1 | "Normalize 'chest pain' as a Problem" | `normalize_ppml_term` | | |
| 2 | "Search for the medical term 'diabetes mellitus'" | `search_medical_term` | | |
| 3 | "Extract entities from: Patient with COPD exacerbation and acute kidney injury on metformin" | `entity_extraction` | | |
| 4 | "Get ICD-10 mappings for IMO lexical code 123456" | `get_mappings` | | |
| 5 | "What refinements are available for hypertension?" | `normalize_ppml_term` → `get_allowed_refinements` | | |
| 6 | "Show the hierarchy around knee pain" | `normalize_ppml_term` → `get_narrower_hierarchy` | | |
| 7 | "What problems are treated by amoxicillin?" | `normalize_ppml_term` → `get_related_problems` | | |
| 8 | "Categorize these problems: diabetes, hypertension, COPD, asthma" | `categorize_problems` | | |

### 2.2 Indirect Requests (same goal, different phrasing)

| # | Prompt | Expected Tool(s) | Actual Tool(s) | Result |
|---|---|---|---|---|
| 1 | "What's the ICD-10 code for type 2 diabetes with kidney disease?" | `normalize_ppml_term` → `get_mappings` | | |
| 2 | "Break down this clinical note into structured data: 65yo M with CHF, afib, on warfarin" | `entity_extraction` | | |
| 3 | "How can I make 'heart failure' more specific?" | `normalize_ppml_term` → `get_lexical` → `get_allowed_refinements` | | |
| 4 | "Translate SNOMED 22298006 to ICD-10" | `get_mappings` or `search_medical_term` → `get_mappings` | | |

### 2.3 Follow-Up Requests (reuse prior results)

| # | Setup → Follow-up | Expected Behavior | Result |
|---|---|---|---|
| 1 | "Normalize 'diabetes'" → "Now show its hierarchy" | Uses lexical_code from step 1 in `get_narrower_hierarchy` | |
| 2 | "What refinements for knee pain?" → "Apply laterality: right" | Uses refinement code in `get_narrower_with_refinements` | |
| 3 | "Extract entities from [note]" → "Get details on the first problem" | Uses lexical code from extraction in `get_term_detail` | |

### 2.4 Negative Requests (should NOT call IMO tools)

| # | Prompt | Expected | Result |
|---|---|---|---|
| 1 | "What's the weather today?" | No IMO tools called | |
| 2 | "Write a Python function to sort a list" | No IMO tools called | |
| 3 | "Summarize this PDF for me" | No IMO tools called | |
| 4 | "What is ICD-10?" (general knowledge, no lookup) | No IMO tools called (or optional) | |

---

## Phase 3: Skill Evaluation

### 3.1 Skill Activation

| # | Prompt | Expected Skill | Activated? | Correct Workflow? |
|---|---|---|---|---|
| 1 | "Set up the IMO Health connection" | setup | | |
| 2 | "Normalize 'acute bronchitis' and get all code mappings" | normalize-term | | |
| 3 | "Find the most specific ICD-10 for type 2 diabetes with retinopathy" | diagnosis-specificity | | |
| 4 | "Extract all diagnoses from this discharge summary: [text]" | entity-extraction | | |
| 5 | "Map ICD-10 code E11.9 to SNOMED" | cross-code-mapping | | |
| 6 | "Explore the knowledge graph starting from 'pneumonia'" | knowledge-graph-explorer | | |

### 3.2 Multi-Tool Workflow Chains

| # | Scenario | Expected Tool Chain | Complete? |
|---|---|---|---|
| 1 | Specificity drill: "Most specific ICD-10 for type 2 diabetes with nephropathy" | `normalize_ppml_term` → `get_lexical` → `get_allowed_refinements` → `get_narrower_sequential_refinements` → `get_mappings` | |
| 2 | NLP + categorize: "Extract problems from [note] and categorize them" | `entity_extraction` → `categorize_problems` | |
| 3 | Cross-domain: "What medications treat COPD?" | `normalize_ppml_term` → `get_cross_domain` | |
| 4 | Reverse lookup: "What conditions does metformin treat?" | `normalize_ppml_term` (Medication) → `get_related_problems` | |

---

## Phase 4: Error & Edge Cases

| # | Test Case | Expected Behavior | Result |
|---|---|---|---|
| 1 | Invalid/nonexistent IMO lexical code | Useful error message, not crash | |
| 2 | Empty text to entity extraction | Empty results or clear "no entities found" | |
| 3 | Misspelled medical term normalization | Best-match result or "no match" | |
| 4 | Wrong domain (e.g., procedure term in Problem domain) | Graceful handling, suggest correct domain | |
| 5 | OAuth token expired mid-session | Re-authentication prompt | |
| 6 | Very long clinical note (5000+ chars) | Processes without timeout | |

---

## Phase 5: Pre-Submission Checklist

| Check | Status |
|---|---|
| Each skill activates for intended requests | |
| Similar phrasing produces consistent behavior | |
| Unsupported requests don't activate the plugin | |
| All bundled file paths resolve after installation | |
| Starter prompts (defaultPrompt) represent completable workflows | |
| Skills and MCP tools work together as intended | |
| Authentication works after fresh installation | |
| Tool list matches 15 documented capabilities | |
| Structured results match declared output schemas | |
| Authentication failures return useful errors | |
