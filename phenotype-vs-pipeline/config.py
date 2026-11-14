"""
Configuration for Phenotype → Value Set Pipeline (Normalize + KG + Precision Sets).
Credentials and paths are injected via environment variables.
"""

import os

# OAuth
IMO_AUTH_URL = "https://api.imohealth.com/oauth/token"
IMO_AUDIENCE = "https://api.imohealth.com"

# Normalize API (production)
IMO_NORMALIZE_URL = "https://api.imohealth.com/precision/normalize"
IMO_NORMALIZE_CLIENT_ID = os.environ.get("IMO_NORMALIZE_CLIENT_ID", "")
IMO_NORMALIZE_CLIENT_SECRET = os.environ.get("IMO_NORMALIZE_CLIENT_SECRET", "")

# Knowledge Graph GOAT API (production)
KG_AUTH_URL = "https://api.imohealth.com/oauth/token"
KG_AUDIENCE = "https://api.imohealth.com"
KG_GRAPHQL_URL = "https://api.imohealth.com/knowledgegraph/graphql/"
IMO_KG_CLIENT_ID = os.environ.get("IMO_KG_CLIENT_ID", "")
IMO_KG_CLIENT_SECRET = os.environ.get("IMO_KG_CLIENT_SECRET", "")

# Precision Sets API
PS_AUTH_URL    = os.environ.get("PS_AUTH_URL",    "https://api-dev.imohealth.com/oauth/token")
PS_AUDIENCE    = os.environ.get("PS_AUDIENCE",    "https://api-dev.imohealth.com")
PS_GRAPHQL_URL = os.environ.get("PS_GRAPHQL_URL", "https://api-dev.imohealth.com/v1/value-sets/graphql")
PS_FHIR_URL    = os.environ.get("PS_FHIR_URL",    "https://api-dev.imohealth.com/fhir/r6")
PS_FHIR_SCOPE_PREFIX = "Phenotype Value Set"
PS_CLIENT_ID     = os.environ.get("PS_CLIENT_ID", "")
PS_CLIENT_SECRET = os.environ.get("PS_CLIENT_SECRET", "")
PS_BATCH_SIZE    = 200

# Paths
SPREADSHEET_PATH = os.environ.get("SPREADSHEET_PATH", "")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./phenotype_output")

# Pipeline Settings
VALUESET_VERSION = "1.0"
VALUESET_ATTRIBUTE_VERSION = "2.26.10.1"
NORMALIZE_TOP_N = 1
NORMALIZE_SCORE_THRESHOLD = 0.9
SUPPORTED_DOMAINS = {"Problem", "Procedure", "Medication"}

# Maps free-text domain labels from the spreadsheet to pipeline domain names.
DOMAIN_MAP = {
    "problem": "Problem",
    "condition": "Problem",
    "procedure": "Procedure",
    "procedure: diagnostic (tests)": "Procedure",
    "procedure: therapeutic": "Procedure",
    "medication": "Medication",
    "vaccine": "Medication",
}

# Code system used for Include/Exclude rules, per domain.
# The server does cross-mapping (e.g. IMO_PROBLEM → ICD-10-CM + SNOMED CT).
DOMAIN_CODE_SYSTEM = {
    "Problem": "IMO_PROBLEM",
    "Procedure": "IMO_PROCEDURE",
    # Medication is handled specially: RX_NORM + NDC Include rules.
}
