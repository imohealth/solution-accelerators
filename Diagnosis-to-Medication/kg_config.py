"""
Configuration for IMO Normalize API and Knowledge Graph (GOAT) API.
Credentials are loaded from SSM or environment variables.
"""

import os
import boto3

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def get_ssm_param(name, with_decryption=True):
    try:
        ssm = boto3.client("ssm", region_name=AWS_REGION)
        param = ssm.get_parameter(Name=name, WithDecryption=with_decryption)
        return param["Parameter"]["Value"]
    except Exception:
        return None


# IMO OAuth
IMO_AUTH_URL = "https://api.imohealth.com/oauth/token"
IMO_AUDIENCE = "https://api.imohealth.com"

# Normalize API
IMO_NORMALIZE_URL = "https://api.imohealth.com/precision/normalize"
IMO_NORMALIZE_CLIENT_ID = (
    get_ssm_param("/diagnosis-specificity-agent/imo_normalize_client_id")
    or os.getenv("IMO_NORMALIZE_CLIENT_ID", "")
    or os.getenv("IMO_CLIENT_ID", "")
)
IMO_NORMALIZE_CLIENT_SECRET = (
    get_ssm_param("/diagnosis-specificity-agent/imo_normalize_client_secret")
    or os.getenv("IMO_NORMALIZE_SECRET", "")
    or os.getenv("IMO_CLIENT_SECRET", "")
)

# Knowledge Graph (GOAT) API
KG_GRAPHQL_URL = "https://api.imohealth.com/knowledgegraph/graphql/"
IMO_KG_CLIENT_ID = (
    get_ssm_param("/diagnosis-specificity-agent/imo_kg_client_id")
    or os.getenv("IMO_KG_CLIENT_ID", "")
)
IMO_KG_CLIENT_SECRET = (
    get_ssm_param("/diagnosis-specificity-agent/imo_kg_client_secret")
    or os.getenv("IMO_KG_CLIENT_SECRET", "")
)
