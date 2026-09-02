"""
Configuration for IMO Normalize API and Knowledge Graph (GOAT) API.
"""

import os
import boto3


# IMO OAuth
IMO_AUTH_URL = "https://api.imohealth.com/oauth/token"
IMO_AUDIENCE = "https://api.imohealth.com"

# Normalize API
IMO_NORMALIZE_URL = "https://api.imohealth.com/precision/normalize"
IMO_NORMALIZE_CLIENT_ID = (
    os.getenv("IMO_NORMALIZE_CLIENT_ID", "")
    or os.getenv("IMO_CLIENT_ID", "")
)
IMO_NORMALIZE_CLIENT_SECRET = (
    os.getenv("IMO_NORMALIZE_SECRET", "")
    or os.getenv("IMO_CLIENT_SECRET", "")
)

# Knowledge Graph (GOAT) API
KG_GRAPHQL_URL = "https://api.imohealth.com/knowledgegraph/graphql/"
IMO_KG_CLIENT_ID = os.getenv("IMO_KG_CLIENT_ID", "")
IMO_KG_CLIENT_SECRET = os.getenv("IMO_KG_CLIENT_SECRET", "")
