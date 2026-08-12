# IMO Health MCP Server for Codex

Connect Codex to IMO Health's clinical terminology MCP server for terminology normalization, clinical search, knowledge-graph navigation, and code-system cross-mapping.

## Features

- **Clinical terminology tools** — `normalize_problem`, `normalize_procedure`, `normalize_code`, `batch_normalize`, `search_problem`, `search_code`, `get_suggestions`, `get_relationships`, `get_hierarchy`, and `cross_map`.
- **Natural language interface** — ask questions in plain English; Codex calls the right MCP tools behind the scenes.
- **Multi-system code mapping** — translate between ICD-10-CM, SNOMED CT, CPT, and IMO vocabularies in one step.
- **Knowledge graph navigation** — explore concept relationships, parent/child hierarchies, and related terms.
- **Plugin-based setup** — install from the repository marketplace with guided authentication in ChatGPT desktop app or Codex CLI.
- **Guided onboarding** — run `/mcp` to verify connection status and tool availability.
- **Clinical-use guardrails** — normalize documented terms before selecting codes; never infer undocumented specificity.

---

## What this package contains

The Codex integration is a repository plugin:

- `MCP-Codex/plugins/imo-health/.codex-plugin/plugin.json` — plugin metadata
- `MCP-Codex/plugins/imo-health/.mcp.json` — IMO's Streamable HTTP MCP configuration
- `MCP-Codex/plugins/imo-health/skills/imo-mcp-connect/SKILL.md` — setup, troubleshooting, and safe-use guidance
- `.agents/plugins/marketplace.json` — the repository marketplace entry, which points to the plugin under `MCP-Codex/`

## Install from this repository

Add the repository marketplace, pinning the Codex branch:

```bash
codex plugin marketplace add imohealth/solution-accelerators \\
  --ref add-mcp-codex-guide \\
  --sparse .agents/plugins \\
  --sparse MCP-Codex
```

Restart the ChatGPT desktop app. Open **Plugins**, choose **IMO Health**, and install **IMO Health MCP**. Then open **Settings → MCP servers**, select **IMO Health**, and choose **Authenticate**. In a Codex task, use `/mcp` to verify that the server is connected.

Codex CLI, the ChatGPT desktop app, and the Codex IDE extension share MCP configuration on the same host.

## Authentication compatibility

The IMO Health Claude configuration supplies a user-specific OAuth `clientId` and confidential `clientSecret`. Codex supports MCP OAuth and can receive a client ID, but its normal MCP setup does not accept a client secret. Therefore, the plugin will authenticate directly only if IMO supports dynamic client registration or provides a Codex-compatible public OAuth client using PKCE.

If IMO must retain a per-user confidential client secret, add a local authentication bridge or an IMO-hosted token-broker before claiming a fully automated Codex install. Do not put consumer secrets in plugin files, shell profiles, or source control.

## Clinical-use note

Use the server for terminology assistance. Confirm results against the available clinical documentation and applicable organizational coding policies; do not infer undocumented specificity.
