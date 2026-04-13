<img src="./static/imo_health.png" alt="IMO Health Logo" width="300"/>

--

# IMO Coding Intelligence Notebooks

This folder contains a small notebook workflow for authenticating to the IMO Coding Intelligence API, validating code sets, and checking CMS Excludes 1 conflicts.

## Contents

### 1. `notebooks/01_Setup_and_Authentication.ipynb`
Introduces the IMO Coding Intelligence API authentication flow.

What it does:
- Installs the basic Python packages used by the notebooks
- Loads API credentials from `notebooks/config.json`
- Requests an OAuth access token from the IMO API
- Confirms that authentication is working before you move to the next notebook

Use this notebook first.

### 2. `notebooks/02_Upload_Codes_and_Validate.ipynb`
Shows how to send diagnosis codes to the Coding Intelligence validation endpoint.

What it does:
- Loads credentials from `notebooks/config.json`
- Authenticates with the IMO API
- Builds a code payload manually or from tabular input
- Calls the `imo-admin-coding-sets` endpoint
- Parses results such as non-primary and unspecified code findings

Use this notebook after Notebook 1.

### 3. `notebooks/03_Excludes1_Conflict_Check.ipynb`
Demonstrates CMS Excludes 1 conflict detection.

What it does:
- Authenticates with the IMO API
- Submits ICD-10-CM codes to the `cms-excludes1` endpoint
- Parses conflicting code pairs returned by the API
- Displays a readable conflict report

Use this notebook after Notebook 1 when you want Excludes 1 analysis.

### 4. `notebooks/config.json`
Stores the notebook configuration used for authentication.

Expected structure:
```json
{
  "auth0": {
    "domain": "api.imohealth.com",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "audience": "https://api.imohealth.com"
  },
  "api": {
    "base_url": "https://api.imohealth.com"
  }
}
```

## Prerequisites

You need:
- Python 3.10+
- Jupyter Notebook or JupyterLab
- Valid IMO Coding Intelligence API credentials
- Network access to `https://api.imohealth.com`

## Installation

From the `CodingIntelligence` folder, create and activate a virtual environment.

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install jupyter requests pandas
```

### Windows
```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install jupyter requests pandas
```

## Configuration

Edit `notebooks/config.json` and set:
- `auth0.client_id`
- `auth0.client_secret`

The notebooks already expect credentials to come from this file.

## How To Run

From the `CodingIntelligence` folder:

```bash
source .venv/bin/activate
jupyter notebook
```

Then open the notebooks in this order:
1. `notebooks/01_Setup_and_Authentication.ipynb`
2. `notebooks/02_Upload_Codes_and_Validate.ipynb`
3. `notebooks/03_Excludes1_Conflict_Check.ipynb`

If you are using VS Code, you can also open the folder and run the notebooks directly in the notebook editor after selecting your Python environment.

## Recommended Run Order

1. Run Notebook 1 to verify authentication works.
2. Run Notebook 2 to validate coding sets.
3. Run Notebook 3 to check Excludes 1 conflicts.

## Troubleshooting

If authentication fails:
- Confirm `notebooks/config.json` contains valid credentials.
- Confirm the `audience` is `https://api.imohealth.com`.
- Confirm your environment can reach `https://api.imohealth.com/oauth/token`.

If a notebook cannot find `config.json`:
- Start Jupyter from the `CodingIntelligence` folder.
- Verify the file exists at `notebooks/config.json`.

If imports fail:
- Re-activate the virtual environment.
- Reinstall dependencies with `pip install jupyter requests pandas`.
