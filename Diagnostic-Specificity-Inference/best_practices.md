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

| # | Scenario | Mode | KG Edge Used | Tools | Complexity |
|---|----------|------|-------------|-------|------------|
| 1 | Diagnosis Specificity using Problems | `ds-conditions` | `refinementNarrower` | 4 | High — multi-step refinement groups |
| 2 | Refine Diagnosis using Medication | `refine` | `domainNarrowerByMedications` + `refinementNarrower` | 9 | Highest — two-phase (med drill-down + refinement) |
| 3 | Rank Diagnosis using Medication | `rank` | `treatedProblems` / `preventedProblems` / `causedProblems` | 2 | Medium — scoring formula |
| 4 | Diagnosis Specificity using Medication | `dx-infer` | `domainNarrowerByMedications` | 2 | Low — iterative drill-down |
| 5 | Medication Identification | `med-id` | `domainNarrower` + `containingMedications` | 3 | Medium — medication hierarchy |
| 6 | Diagnosis to Medication | `dx-to-med` | `associatedTreatments` | 2 | Low — single KG lookup |
| 7 | Diagnosis Specificity using Procedure | `dx-infer-proc` | `domainNarrowerByProcedures` | 2 | Low — iterative drill-down |
| 8 | DS using Procedure with Temporality | `procedure_inference` | `domainNarrowerByProcedures` + temporal logic | 2 | Medium — adds temporal context |
| 9 | Lab Identification (Prototype) | `lab-id` | `domainNarrower` (Lab domain) | 2 | Low — lab hierarchy exploration |

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
