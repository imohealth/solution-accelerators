---
name: imo-mcp-connect
description: Set up or troubleshoot the IMO Health MCP server in Codex for clinical terminology normalization, search, and code mapping. Use when the user asks to connect IMO Health, authenticate, or diagnose an IMO MCP issue.
---

# Connect to IMO Health MCP

Use this skill only for setting up or troubleshooting the IMO Health MCP connection.

## Connection

- MCP endpoint: `https://api.imohealth.com/mcp`
- Transport: Streamable HTTP
- Authentication: OAuth 2.0 authorization-code flow
- Requested scopes: `openid`, `profile`, `email`, `normalize`, `normalizeresults`, `search`

## Setup flow

1. Confirm the IMO Health plugin is installed and enabled.
2. In the ChatGPT desktop app, open **Settings → MCP servers**, select **IMO Health**, and choose **Authenticate**. Restart the app if the server does not appear.
3. In Codex CLI, use `codex mcp login imo-health --scopes openid,profile,email,normalize,normalizeresults,search` when the server appears in `codex mcp list`.
4. Verify the connection using `/mcp` in a Codex task or `codex mcp list` in the CLI.

## Expected tools

The server should provide terminology normalization, search, hierarchy, relationship, and cross-mapping tools, including `normalize_problem`, `normalize_procedure`, `normalize_code`, `batch_normalize`, `search_problem`, `search_code`, `get_suggestions`, `get_relationships`, `get_hierarchy`, and `cross_map`.

## Troubleshooting

- If the server is absent, ensure the plugin is enabled, then restart Codex.
- If authentication fails or the browser does not open, capture the MCP error and verify the OAuth callback URL and requested scopes with the IMO Health developer portal.
- Do not ask a user to paste credentials, access tokens, or client secrets into a chat, source file, or repository.
- A user-specific confidential OAuth client requires IMO to provide a Codex-compatible public/PKCE client or dynamic client registration. Codex's normal MCP OAuth setup accepts an OAuth client ID but does not provide a client-secret input.

## Clinical-use guardrails

- Normalize the documented clinical term before selecting a code.
- Do not infer undocumented diagnostic specificity.
- Identify the returned code system and code clearly.
- Treat returned information as terminology assistance, not clinical, coding, billing, or treatment advice.
