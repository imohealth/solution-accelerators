# Knowledge Graph Traversal

This notebook demonstrates querying the IMO Knowledge Graph GraphQL API.

## Notebook

- `01_IMO_Knowledge_Graph_Traversal.ipynb`

What it covers:
- Load credentials from `config.json`
- Get an OAuth access token
- Run a GraphQL query against the Knowledge Graph endpoint
- Pretty-print response mappings in a table with a purple header

## Configuration

Copy `config.json.template` to `config.json` and fill in your credentials.

Example:

```json
{
  "knowledge_graph": {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "token_url": "https://api.imohealth.com/oauth/token",
    "graphql_url": "https://api.imohealth.com/knowledgegraph/graphql/"
  }
}
```

Do not commit `config.json` to source control.
