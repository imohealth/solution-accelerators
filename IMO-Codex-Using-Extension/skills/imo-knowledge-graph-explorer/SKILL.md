---
name: imo-knowledge-graph-explorer
description: Explore the IMO Knowledge Graph schema and run read-only SPARQL queries for advanced clinical terminology research
when_to_use: Use when the user wants to explore the knowledge graph structure, discover named graphs/classes/predicates, run custom SPARQL queries, or perform advanced graph-based research. Triggers on words like "SPARQL", "knowledge graph", "graph schema", "named graphs", "classes", "predicates", "query the graph", "explore schema".
user-invocable: true
---

# Knowledge Graph Explorer — Schema Discovery & SPARQL

You are helping the user explore the IMO Knowledge Graph and run custom SPARQL queries. This skill is for advanced users who need direct graph access beyond what the GraphQL tools provide.

## Tools

---

### `explore_schema`

Discover the shape of the IMO Knowledge Graph before writing a SPARQL query. Always run this first to ground your query in observed schema — do not guess predicate names or class IRIs.

**Sections:**

| Section | What it returns |
|---------|----------------|
| `named_graphs` | Lists every named graph (e.g., `urn:x-imo:problem`, `urn:x-imo:procedure`, `urn:x-imo:subrx`, `urn:x-imo:modifier`) |
| `classes` | `rdf:type` values with instance counts, optionally scoped to a named graph |
| `predicates` | Predicates in use with usage counts, optionally scoped to a named graph |
| `sample_class` | 25 triples for an arbitrary instance of `class_iri`, showing predicates and value shapes |

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `section` | `string` | Yes | — | One of: `"named_graphs"`, `"classes"`, `"predicates"`, `"sample_class"` |
| `graph` | `string` or `null` | No | `null` | Named-graph IRI to scope the query (e.g., `"urn:x-imo:problem"`). Applies to `classes`, `predicates`, `sample_class`. |
| `class_iri` | `string` or `null` | No | `null` | Required when `section="sample_class"`. Full IRI of the class to sample instances of. |

**Examples:**

List all named graphs:
```json
{ "section": "named_graphs" }
```

List classes in the problem graph:
```json
{ "section": "classes", "graph": "urn:x-imo:problem" }
```

Sample a class to see its predicates:
```json
{
  "section": "sample_class",
  "graph": "urn:x-imo:problem",
  "class_iri": "http://www.w3.org/2004/02/skos/core#Concept"
}
```

---

### `run_sparql`

Execute a read-only SPARQL query against the IMO Knowledge Graph. Only SELECT, ASK, CONSTRUCT, and DESCRIBE are accepted — write operations are rejected.

A default LIMIT is injected into bare SELECTs to prevent massive result sets. Returns Neptune's SPARQL 1.1 JSON results envelope plus a flat `rows` list-of-dicts view.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | `string` | Yes | — | A read-only SPARQL query (SELECT, ASK, CONSTRUCT, or DESCRIBE) |
| `limit` | `integer` or `null` | No | `null` | Optional LIMIT to inject when the SELECT has none. Capped at 1000; default 100. |

**Example:**
```json
{
  "query": "SELECT ?concept ?label WHERE { ?concept a <http://www.w3.org/2004/02/skos/core#Concept> ; <http://www.w3.org/2004/02/skos/core#prefLabel> ?label . FILTER(CONTAINS(LCASE(?label), 'diabetes')) }",
  "limit": 20
}
```

---

## How to Use

### Recommended Workflow

Always discover the schema before querying:

```
Step 1: explore_schema (section: "named_graphs")
  → See what graphs exist (problem, procedure, medication, modifier, etc.)

Step 2: explore_schema (section: "classes", graph: "urn:x-imo:problem")
  → See what classes exist in the graph you care about

Step 3: explore_schema (section: "predicates", graph: "urn:x-imo:problem")
  → See what predicates are available

Step 4: explore_schema (section: "sample_class", class_iri: "<chosen_class>")
  → See real triples to understand the data shape

Step 5: run_sparql (query: "<your query>")
  → Query with confidence based on observed schema
```

### Important Rules

1. **Always call `explore_schema` before writing SPARQL** — do not guess predicate names or class IRIs
2. **Only read queries** — SELECT, ASK, CONSTRUCT, DESCRIBE. No INSERT, DELETE, LOAD, CLEAR, DROP.
3. **Use LIMIT** — either in your query or via the `limit` parameter. Default is 100, max is 1000.
4. **Scope queries to named graphs** when possible for better performance

## Chaining to Other Skills

- **For structured GraphQL access** → use `imo-graphql` instead (mappings, hierarchy, refinements, cross-domain)
- **Need a lexical code to anchor your query?** → use `imo-normalize` or `imo-core-search` first
- **Want editorial/policy guidance?** → use `imo-concept-guideline` with `search_editorial_kb`
