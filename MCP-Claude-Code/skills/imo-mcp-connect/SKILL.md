---
name: imo-mcp-connect
description: Set up credentials and authenticate with the IMO Health MCP server for clinical terminology normalization, search, and knowledge graph access
when_to_use: Use when the user wants to set up credentials for the IMO Health MCP server, authenticate, or troubleshoot their IMO Health MCP connection
user-invocable: true
allowed-tools: Bash Read
---

# Set Up IMO Health MCP Credentials

You are helping the user configure credentials for the IMO Health MCP gateway. The MCP server itself is already registered by this plugin — you only need to ensure the required environment variables are set and authentication completes.

## Server Info

- **Server URL:** `https://api.imohealth.com/mcp`
- **Authentication:** OAuth 2.0 (Authorization Code Flow)
- **Required env vars:** `IMO_CLIENT_ID`, `MCP_CLIENT_SECRET`

## Step 1: Check for Existing Credentials

Check `~/.zshrc` (and `~/.bashrc` as fallback) for existing environment variables:

```bash
grep -E '(IMO_CLIENT_ID|IMO_CLIENT_SECRET|MCP_CLIENT_SECRET)' ~/.zshrc ~/.bashrc 2>/dev/null
```

- If `IMO_CLIENT_ID` is found, use it as the Client ID.
- If `IMO_CLIENT_SECRET` or `MCP_CLIENT_SECRET` is found, use it as the Client Secret.

If **both** values are found, inform the user and skip to Step 3.

If credentials are **not** found, ask the user for their **Client ID** and **Client Secret** from the IMO Health developer portal.

If they don't have credentials yet, direct them to:

1. Go to https://developer.imohealth.com
2. Click **Log in** → **Create Account**
3. Complete registration and activate via email
4. Navigate to **My Credentials** (`/user/apps`)
5. Click **+ New Trial**, name the app, select APIs, click **Create Trial App**
6. Click the **View** icon to reveal:
   - **Consumer Key** = Client ID
   - **Consumer Secret** = Client Secret

Do NOT proceed until credentials are available.

## Step 2: Set Environment Variables

Ensure both `IMO_CLIENT_ID` and `MCP_CLIENT_SECRET` are exported in `~/.zshrc`:

```bash
grep 'IMO_CLIENT_ID' ~/.zshrc 2>/dev/null
grep 'MCP_CLIENT_SECRET' ~/.zshrc 2>/dev/null
```

For any that are missing, add them:

```bash
echo 'export IMO_CLIENT_ID="<their_client_id>"' >> ~/.zshrc
echo 'export MCP_CLIENT_SECRET="<their_client_secret>"' >> ~/.zshrc
```

If `IMO_CLIENT_SECRET` exists but `MCP_CLIENT_SECRET` does not, alias it:

```bash
echo 'export MCP_CLIENT_SECRET="$IMO_CLIENT_SECRET"' >> ~/.zshrc
```

Then source the file:

```bash
source ~/.zshrc
```

## Step 3: Authenticate via Browser

The plugin has already registered the MCP server. When Claude Code connects for the first time, it will:

1. Open the browser to `https://api.imohealth.com/mcp/authorize`
2. Prompt the user to log in with their IMO Health credentials
3. Request access to scopes: `openid profile email normalize normalizeresults search`
4. Redirect back to Claude Code with an authorization code
5. Exchange the code for an access token

This happens automatically. The token is refreshed automatically when it expires.

**Important:** After the first connection, Claude Code generates a redirect URL. This URL must be added to the Auth0 Allowed Callback URLs in the IMO developer portal.

Tell the user to start a new Claude Code session if they haven't authenticated yet — the OAuth flow triggers on first connection.

## Step 4: Verify the Connection

Tell the user to run `/mcp` in Claude Code. Confirm `imo-health` appears and lists these tools:

**Precision Normalization:**
- `normalize_problem` — Normalize problems to standard clinical terminology and code mappings
- `normalize_procedure` — Normalize procedures to standard clinical terminology
- `normalize_code` — Normalize a source code (ICD or SNOMED) to the current IMO identifier
- `batch_normalize` — Process multiple terms or codes in a single request

**Core Search:**
- `search_problem` — Search clinical concepts by free-text query
- `search_code` — Search clinical concepts by code (ICD, SNOMED, CPT, etc.)
- `get_suggestions` — Autocomplete suggestions for partial clinical text

**Knowledge Graph:**
- `get_relationships` — Retrieve relationships and associations for a clinical concept
- `get_hierarchy` — Navigate parent/child hierarchy of a clinical knowledge system
- `cross_map` — Map concepts across coding systems (ICD-10, SNOMED CT, CPT, etc.)

## Troubleshooting

**"Needs authentication" in `/mcp`:**
- Start a new Claude Code session to trigger the OAuth browser flow
- Ensure `MCP_CLIENT_SECRET` env var is set in the current shell (`echo $MCP_CLIENT_SECRET`)

**OAuth browser window doesn't open:**
- Restart Claude Code
- Check that the default browser can be opened from the terminal

**401 Unauthorized:**
- Token expired — Claude Code should auto-refresh
- If refresh fails, remove and re-add the server:
  ```bash
  claude mcp remove imo-health
  ```
  Then restart Claude Code — the plugin will re-register the server automatically.

**Redirect URI mismatch:**
- After first connection, copy the callback URL from Claude Code
- Add it to Auth0 Allowed Callback URLs in the IMO developer portal

**429 Too Many Requests:**
- Rate limit hit — wait and retry
- Check the `Retry-After` response header
