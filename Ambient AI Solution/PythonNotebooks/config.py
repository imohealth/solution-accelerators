"""
Configuration file for Ambient AI Solution
Store API credentials and settings here
"""

# AWS Bedrock Configuration
aws_region = "us-east-1"  # Change to your preferred region
aws_access_key_id = ""  # Update your AWS credentials 
aws_secret_access_key = ""  # Update your AWS credentials 
aws_session_token = ""  # Update your AWS credentials 
bedrock_model_id = "us.amazon.nova-pro-v1:0"  # Amazon Nova Pro model

import boto3
import os
from botocore.exceptions import ClientError

imo_entity_extraction_client_id = ""  # Update with your IMO API client ID
imo_entity_extraction_client_secret = ""  # Update with your IMO API client secret
imo_normalize_enrichment_api_client_id = "" # Update with your IMO API client ID
imo_normalize_enrichment_api_client_secret = "" # Update with your IMO API client secret
imo_diagnostic_workflow_client_id = ""	# Update with your IMO API client ID
imo_diagnostic_workflow_client_secret = "	"# Update with your IMO API client secret

# API Endpoints
imo_auth_url = "https://api.imohealth.com/oauth/token"
imo_entity_extraction_url = "https://api.imohealth.com/entityextraction/pipelines/imo-clinical-comprehensive?version=3.0"
imo_precision_normalize_enrichment_url = "https://api.imohealth.com/precision/normalize/enrichment"
imo_precision_normalize_url = "https://api.imohealth.com/precision/normalize"
imo_diagnostic_workflow_url = "https://api.imohealth.com/core/search/v2/product/problemIT_Professional/workflows/diagnosis"

