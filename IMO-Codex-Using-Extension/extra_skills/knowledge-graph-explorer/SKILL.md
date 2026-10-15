---
name: knowledge-graph-explorer
description: Navigate the IMO Clinical Knowledge Graph — explore hierarchies, cross-domain relationships, refinements, and related clinical concepts.
---

# Knowledge Graph Explorer

Interactively explore the IMO Health Clinical Knowledge Graph to discover relationships between clinical concepts.

## Capabilities

This skill provides guided access to the Knowledge Graph tools:

- **Hierarchy navigation** — browse parent/child relationships up and down the problem taxonomy
- **Refinement exploration** — discover what modifiers (laterality, chronicity, severity, etc.) can be applied
- **Cross-domain relationships** — find related diagnostics, treatments, procedures, causes, and complications
- **Reverse lookups** — find what problems a procedure treats or a medication addresses

## Workflow

1. **Get the starting concept** from the user — a medical term, IMO lexical code, or a description of what they want to explore.

2. **Normalize** (if starting from text) using `normalize-ppml___normalize_ppml_term` to get the `lexical_code`.

3. **Based on what the user wants to explore**, use the appropriate tool:

   | User Intent | Tool |
   |---|---|
   | "What's above/below this in the hierarchy?" | `graphql-modifier___get_narrower_hierarchy` |
   | "What refinements can I apply?" | `graphql-modifier___get_allowed_refinements` |
   | "Show all options in a refinement group" | `graphql-modifier___get_refinement_group` |
   | "What's related to this diagnosis?" | `graphql-modifier___get_cross_domain` |
   | "What problems does this procedure/drug treat?" | `graphql-modifier___get_related_problems` |
   | "Filter children by a specific refinement" | `graphql-modifier___get_narrower_with_refinements` |
   | "Drill down through multiple refinements" | `graphql-modifier___get_narrower_sequential_refinements` |
   | "Look up this lexical's full details" | `graphql-modifier___get_lexical` |

4. **Present results** clearly and offer to continue exploring:
   - Show the current position in the hierarchy
   - List available next steps (deeper hierarchy, refinements, cross-domain, mappings)
   - Let the user navigate interactively

5. **At any point**, offer to retrieve code mappings via `graphql-modifier___get_mappings` for any lexical the user is interested in.

## Tips
- Always use `lexical_code`, never `imo_code`.
- Hierarchy and refinement tools work only in the Problem domain.
- Cross-domain and related-problems tools work across Problem, Procedure, and Medication domains.
- Encourage iterative exploration — the Knowledge Graph is deep and richly connected.
