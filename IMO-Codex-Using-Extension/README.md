# IMO Health Clinical Intelligence Plugin

Clinical terminology normalization, knowledge graph navigation, and code-system cross-mapping powered by IMO Health MCP.

## What This Plugin Does

Connect to IMO Health's MCP server to access 19 clinical terminology tools:

- **Normalize** medical terms across Problem, Procedure, Medication, and Lab domains
- **Search** clinical concepts by free text or code
- **Map** between ICD-10-CM, SNOMED CT, CPT, RxNorm, HCPCS, LOINC, and 10+ code systems
- **Navigate** the IMO Knowledge Graph — hierarchies, refinements, cross-domain relationships
- **Extract** clinical entities from free-text notes (discharge summaries, progress notes)
- **Categorize** problem lists by disease category
- **Drill down** to the most specific ICD-10 code using diagnosis specificity refinements

## Prerequisites

- **Node.js** (v18+) — https://nodejs.org
- **OpenAI Codex CLI** — install with `npm install -g @openai/codex`
- **Python** (for setup script)
- **Git**
- **IMO Health credentials** (Client ID and Client Secret) — contact your IMO team

## Quick Start (Automated)

```bash
# 1. Clone the repo
git clone <repo-url>
cd IMO-Codex-Using-Extension

# 2. Run setup
bash setup.sh
```

The setup script will:
1. Register the local marketplace
2. Install the plugin
3. Prompt for your IMO credentials (Client ID and Client Secret)
4. Add the MCP server to your Codex config

After setup:
```bash
# 3. Launch Codex
codex

# 4. Authenticate the MCP server
/mcp login IMO-HEALTH-MCP-SERVER

# 5. Verify connection
/mcp
# Should show: IMO-HEALTH-MCP-SERVER: connected (19 tools)

# 6. Test it
Normalize chest pain
```

## Manual Setup

If you prefer to set up manually instead of using `setup.sh`:

### Step 1 — Register the marketplace

```bash
codex plugin marketplace add /path/to/IMO-Codex-Using-Extension
```

### Step 2 — Install the plugin

```bash
codex plugin add imo-health-clinical-intelligence@imo-health-codex-marketplace
```

### Step 3 — Set credentials

**Bash (Mac/Linux/Git Bash):**
```bash
export IMO_CLIENT_ID="<your-client-id>"
export MCP_CLIENT_SECRET="<your-client-secret>"
```

To make permanent:
```bash
echo 'export IMO_CLIENT_ID="<your-client-id>"' >> ~/.bashrc
echo 'export MCP_CLIENT_SECRET="<your-client-secret>"' >> ~/.bashrc
source ~/.bashrc
```

**PowerShell (Windows):**
```powershell
$env:IMO_CLIENT_ID="<your-client-id>"
$env:MCP_CLIENT_SECRET="<your-client-secret>"
```

### Step 4 — Add MCP server to Codex config

Add this block to `~/.codex/config.toml`:

```toml
[mcp_servers.IMO-HEALTH-MCP-SERVER]
enabled = true
url = "https://api.imohealth.com/mcp"
```

**PowerShell (Windows):**
```powershell
Add-Content ~/.codex/config.toml "`n[mcp_servers.IMO-HEALTH-MCP-SERVER]`nenabled = true`nurl = `"https://api.imohealth.com/mcp`""
```

### Step 5 — Launch and authenticate

```bash
codex
```

Inside Codex:
```
/mcp login IMO-HEALTH-MCP-SERVER
```

### Step 6 — Verify

```
/mcp
```

You should see `IMO-HEALTH-MCP-SERVER: connected (19 tools)`.

### Step 7 — Verify in Codex Settings

Open Codex settings to confirm the plugin and marketplace are visible:

1. Open **Codex Settings** (gear icon or `/settings`)
2. Go to the **Plugins** section
3. You should see:
   - **Marketplace:** `imo-health-codex-marketplace` listed as a local source
   - **Plugin:** `IMO Health Clinical Intelligence` installed and enabled

## ChatGPT Web Plugin

This plugin can also be used on ChatGPT web:

1. Go to chatgpt.com/plugins
2. Click **+** then **Upload plugin archive**
3. Upload the plugin ZIP (containing `plugin.json`, `mcp.json`, `skills/`)
4. Connect the MCP server through the portal
5. Test in a new chat

## Available Skills

| Skill | Description |
|-------|-------------|
| **imo-clinical-tools** | Master guide to all 19 MCP tools — decision tree, workflows, formatting rules |
| **setup** | Installation and authentication walkthrough |

## Project Structure

**Local Marketplace (Codex CLI):**
```
.mcp.json                    # MCP server config for Codex CLI
.codex-plugin/
  plugin.json                # Codex compatibility manifest
.agents/plugins/
  marketplace.json           # Local marketplace discovery
.app.json                    # MCP server ID mapping (workspace publish)
setup.sh                     # Automated setup script
```

**ChatGPT Plugin ZIP (public submission):**
```
plugin.json                  # Portable plugin manifest
mcp.json                     # MCP server config with OAuth
skills/
  imo-clinical-tools/        # Master tool guide (all 19 tools)
  setup/                     # Installation guide
assets/
  logo.png                   # Plugin logo
  screenshots/               # Plugin screenshots
```

**Shared (used by both):**
```
skills/                      # AI instructions for using MCP tools
assets/                      # Logo and screenshots
```

## Example Queries

Try these after setup:

```
Normalize "type 2 diabetes with kidney disease" and find the most specific ICD-10 code
```

```
Extract all clinical entities from this discharge summary: "Patient presents with chest pain, shortness of breath, and elevated troponin levels"
```

```
What refinements are available for hypertension?
```

```
Map SNOMED code 22298006 to ICD-10-CM
```

```
What procedures are associated with congestive heart failure?
```

## Troubleshooting

### "codex: command not found"
Install Codex CLI:
```bash
npm install -g @openai/codex
```

### MCP server shows "needs authentication"
Run inside Codex:
```
/mcp login IMO-HEALTH-MCP-SERVER
```

### OAuth browser window doesn't open
Restart Codex and try again. Ensure your default browser can be opened from the terminal.

### 401 Unauthorized
Token expired. Codex should auto-refresh. If it doesn't:
```bash
codex mcp remove IMO-HEALTH-MCP-SERVER
```
Then restart Codex — the plugin will re-register the server.

### 429 Too Many Requests
Rate limit hit. Wait and retry. Check the `Retry-After` response header.

### Credentials not working
Verify your environment variables are set:
```bash
echo $IMO_CLIENT_ID
echo $MCP_CLIENT_SECRET
```

## Support

- IMO Health: https://www.imohealth.com
- Developer Portal: https://developer.imohealth.com
