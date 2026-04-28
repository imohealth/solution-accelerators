# Knowledge Graph Traversal

This notebook demonstrates querying the IMO Knowledge Graph GraphQL API.

## Notebook

- `IMO_Knowledge_Graph_Traversal.ipynb`

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

## How to Run

1. Open a terminal in this folder (`knowledge-graph-accelerator/src/notebooks/Knowledge_Graph_Traversal`).

2. Create your runtime config:

```bash
cp config.json.template config.json
```

3. Edit `config.json` and provide valid IMO `client_id` and `client_secret`.

4. Start Jupyter (either command works):

```bash
jupyter notebook
# or
jupyter lab
```

5. In Jupyter, open `IMO_Knowledge_Graph_Traversal.ipynb` and select a Python kernel.

6. Run cells from top to bottom:
- Step 1 installs dependencies and loads config
- Step 2 gets OAuth token
- Steps 3 onward run Knowledge Graph queries and render tables

7. If package imports fail, rerun Step 1, then rerun the remaining cells.

### Optional: Run in VS Code

- Open `IMO_Knowledge_Graph_Traversal.ipynb` in VS Code.
- Select a Python/Jupyter kernel.
- Run cells in order from Step 1 through the final step.

## Expected Output

- Styled purple-header tables for mappings and hierarchy/refinement queries
- Raw JSON blocks after each query for troubleshooting
