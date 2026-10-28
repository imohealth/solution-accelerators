---
name: setup
description: Guide users through installing and authenticating the IMO Health MCP plugin via marketplace.
---

# IMO Health Plugin Setup

Welcome to the IMO Health Clinical Intelligence plugin. This skill walks you through installing the plugin and connecting to the IMO Health MCP server.

## Prerequisites

- OpenAI Codex CLI installed
- IMO Health credentials (Client ID and Client Secret) from the IMO team
- Git (to clone the plugin repository)

## Install Steps

### Step 1 — Clone the plugin

```bash
git clone <repo-url> IMO-Codex-Using-Extension
cd IMO-Codex-Using-Extension
```

### Step 2 — Register the marketplace

```bash
codex plugin marketplace add --source /path/to/IMO-Codex-Using-Extension
```

### Step 3 — Install the plugin

```bash
codex plugin add imo-health-clinical-intelligence
```

### Step 4 — Set credentials as environment variables

```bash
export IMO_CLIENT_ID="<your-client-id>"
export MCP_CLIENT_SECRET="<your-client-secret>"
```

To make these permanent, add the two export lines to your `~/.bashrc` or `~/.bash_profile`.

### Step 5 — Add MCP server to Codex config

Add this block to `~/.codex/config.toml`:

```toml
[mcp_servers.imo_health_test]
enabled = true
url = "https://api.imohealth.com/mcp"
```

### Step 6 — Launch Codex and verify

```bash
codex
```

Then run `/mcp` to confirm `imo_health_test: connected (19 tools)`.

## Test It

Run a test query: "Normalize the term 'chest pain' in the Problem domain"

If you get back a lexical code and ICD-10-CM mapping, the plugin is working.

## Available Skills

Once connected, you have access to 19 clinical terminology tools and these skills:

- **imo-clinical-tools** — Provides access to 19 clinical terminology tools for normalizing, mapping, and coding clinical terms across various domains such as Problems, Procedures, Medications, and more.
