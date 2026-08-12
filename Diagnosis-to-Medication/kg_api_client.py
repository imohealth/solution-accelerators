"""
Direct HTTP client for IMO Normalize API and Knowledge Graph (GOAT) GraphQL API.
Supports diagnosis-to-medication validation via medicationGroups.
"""

import time
import uuid
import requests
from typing import Any, Dict, List, Optional

import kg_config


class KGApiClient:
    """Client for IMO Normalize + Knowledge Graph APIs with token caching."""

    def __init__(self):
        self._normalize_token: Optional[str] = None
        self._normalize_token_expiry: float = 0
        self._kg_token: Optional[str] = None
        self._kg_token_expiry: float = 0

    def _get_oauth_token(
        self,
        client_id: str,
        client_secret: str,
        audience: Optional[str] = None,
        auth_url: Optional[str] = None,
    ) -> Optional[str]:
        """Get OAuth2 token using client credentials grant."""
        try:
            response = requests.post(
                auth_url or kg_config.IMO_AUTH_URL,
                headers={"Content-Type": "application/json"},
                json={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "audience": audience or kg_config.IMO_AUDIENCE,
                },
                timeout=30,
            )
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                print(f"  [KG API] OAuth error: {response.status_code} - {response.text[:200]}")
                return None
        except Exception as e:
            print(f"  [KG API] OAuth exception: {e}")
            return None

    def _get_normalize_token(self) -> Optional[str]:
        if self._normalize_token and time.time() < self._normalize_token_expiry:
            return self._normalize_token
        token = self._get_oauth_token(
            kg_config.IMO_NORMALIZE_CLIENT_ID,
            kg_config.IMO_NORMALIZE_CLIENT_SECRET,
        )
        if token:
            self._normalize_token = token
            self._normalize_token_expiry = time.time() + 3540  # 59 min
        return token

    def _get_kg_token(self) -> Optional[str]:
        if self._kg_token and time.time() < self._kg_token_expiry:
            return self._kg_token
        token = self._get_oauth_token(
            kg_config.IMO_KG_CLIENT_ID,
            kg_config.IMO_KG_CLIENT_SECRET,
        )
        if token:
            self._kg_token = token
            self._kg_token_expiry = time.time() + 3540
        return token

    # ─── Normalize API ──────────────────────────────────────────────────────

    def normalize_medical_term(self, input_term: str, domain: str = "Problem") -> Dict[str, Any]:
        """Normalize a medical term using IMO Precision Normalize API."""
        token = self._get_normalize_token()
        if not token:
            return {"success": False, "error": "Failed to obtain Normalize API token"}

        payload = {
            "organization_id": "IMO",
            "client_request_id": str(uuid.uuid4()),
            "preferences": {
                "threshold": 0.0,
                "match_field_pref": "input_term",
                "debug": True,
                "size": 1,
            },
            "requests": [
                {
                    "record_id": str(uuid.uuid4()),
                    "domain": domain,
                    "input_term": input_term,
                }
            ],
        }

        try:
            response = requests.post(
                kg_config.IMO_NORMALIZE_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                if "requests" in result and result["requests"]:
                    request_data = result["requests"][0]
                    if "response" in request_data and "items" in request_data["response"]:
                        items = request_data["response"]["items"]
                        if items:
                            matches = []
                            for item in items:
                                icd10_codes = []
                                icd10cm = item.get("metadata", {}).get("mappings", {}).get("icd10cm", {})
                                for c in icd10cm.get("codes", []):
                                    if c.get("code"):
                                        icd10_codes.append(c["code"])
                                matches.append({
                                    "title": item.get("title", ""),
                                    "lexical_code": item.get("lexical_code", ""),
                                    "default_lexical_code": item.get("default_lexical_code", ""),
                                    "score": item.get("score", 0),
                                    "icd10_codes": icd10_codes,
                                })
                            return {"success": True, "results": [{"input_term": input_term, "matches": matches}]}
                return {"success": True, "results": [{"input_term": input_term, "matches": []}]}
            else:
                return {"success": False, "error": f"Normalize API error: {response.status_code} - {response.text[:300]}"}
        except Exception as e:
            return {"success": False, "error": f"Normalize API exception: {str(e)}"}

    # ─── Knowledge Graph (GOAT) GraphQL API ────────────────────────────────

    def _graphql_query(self, query: str, variables: Dict[str, Any], endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against the GOAT KG API."""
        target_url = endpoint or kg_config.KG_GRAPHQL_URL
        token = self._get_kg_token()
        if not token:
            return {"success": False, "error": "Failed to obtain KG API token"}

        try:
            response = requests.post(
                target_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables},
                timeout=30,
            )
            if response.status_code == 200:
                result = response.json()
                if "errors" in result:
                    return {"success": False, "error": "; ".join(e.get("message", "") for e in result["errors"])}
                return {"success": True, "data": result.get("data", {})}
            else:
                return {"success": False, "error": f"KG GraphQL error: {response.status_code} - {response.text[:300]}"}
        except Exception as e:
            return {"success": False, "error": f"KG GraphQL exception: {str(e)}"}

    def get_medication_groups(self, imo_lexical_code: str) -> Dict[str, Any]:
        """
        Get medication groups and their associated medications for a problem concept.

        Args:
            imo_lexical_code: The IMO lexical code of the problem

        Returns:
            Dict with medicationGroups list, each containing code, title, and medications [{code, title}]
        """
        query = """query GetMedicationGroups($code: String!, $domain: IMODomain!) {
  lexical(code: $code, domain: $domain) {
    code
    title
    ... on ProblemLexical {
      medicationGroups {
        code
        title
        medications {
          code
          title
        }
      }
    }
  }
}"""
        variables = {"code": imo_lexical_code, "domain": "problem"}
        result = self._graphql_query(query, variables)
        if result.get("success") and result.get("data"):
            return {"success": True, "lexical": result["data"].get("lexical")}
        return result
