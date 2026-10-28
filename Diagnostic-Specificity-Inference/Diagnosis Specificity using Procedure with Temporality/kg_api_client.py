"""
Direct HTTP client for IMO Normalize API and Knowledge Graph (GOAT) GraphQL API.
Provides: normalize_medical_term, get_temporal_diagnoses.
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
            self._normalize_token_expiry = time.time() + 3540
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

    # --- Normalize API ---

    def normalize_medical_term(self, input_term: str, domain: str = "Procedure", order_name: str = "") -> Dict[str, Any]:
        token = self._get_normalize_token()
        if not token:
            return {"success": False, "error": "Failed to obtain Normalize API token"}

        preferences = {
            "threshold": 0.0,
            "match_field_pref": "input_term",
            "debug": True,
            "size": 1,
        }

        request_entry = {
            "record_id": str(uuid.uuid4()),
            "domain": domain,
            "input_term": input_term,
        }

        if domain == "Lab":
            preferences["use_single_loinc_matching"] = False
            request_entry["input_code"] = ""
            request_entry["input_code_system"] = ""
            request_entry["context"] = {
                "order_name": order_name,
                "unit_of_measure": "",
                "loinc_component": "",
                "loinc_property": "",
                "loinc_method": "",
                "loinc_scale": "",
                "loinc_time": "",
                "sample_type": "",
            }

        payload = {
            "organization_id": "IMO",
            "client_request_id": str(uuid.uuid4()),
            "preferences": preferences,
            "requests": [request_entry],
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
                                metadata = item.get("metadata", {})
                                mappings = metadata.get("mappings", {})
                                icd10_codes = []
                                icd10cm = mappings.get("icd10cm", {})
                                icd10cm_codes = icd10cm.get("codes", [])
                                if isinstance(icd10cm_codes, list):
                                    icd10_codes = [c.get("code", "") for c in icd10cm_codes if c.get("code")]
                                loinc_codes = []
                                loinc = mappings.get("loinc", {})
                                loinc_code_list = loinc.get("codes", [])
                                if isinstance(loinc_code_list, list):
                                    loinc_codes = [
                                        {"code": c.get("code", ""), "title": c.get("title", ""), "map_type": c.get("map_type", "")}
                                        for c in loinc_code_list if c.get("code")
                                    ]
                                title = (
                                    item.get("title")
                                    or item.get("default_lexical_title")
                                    or item.get("lexical_title")
                                    or ""
                                )
                                matches.append({
                                    "title": title,
                                    "lexical_code": item.get("lexical_code", ""),
                                    "default_lexical_code": item.get("default_lexical_code", ""),
                                    "score": item.get("score", 0),
                                    "loinc_codes": loinc_codes,
                                    "icd10_codes": icd10_codes,
                                })
                            resp = {"success": True, "results": [{"input_term": input_term, "matches": matches}]}
                            if domain == "Lab":
                                resp["raw_response"] = result
                            return resp
                return {"success": True, "results": [{"input_term": input_term, "matches": []}]}
            else:
                return {"success": False, "error": f"Normalize API error: {response.status_code} - {response.text[:300]}"}
        except Exception as e:
            return {"success": False, "error": f"Normalize API exception: {str(e)}"}

    # --- Knowledge Graph (GOAT) GraphQL API ---

    def _graphql_query(self, query: str, variables: Dict[str, Any], endpoint: Optional[str] = None) -> Dict[str, Any]:
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

    def get_temporal_diagnoses(self, procedure_code: str) -> Dict[str, Any]:
        """
        Given a procedure code, query ProcedureLexical.associatedProblems to get
        all associated Problem concepts (status post, history of, complications, etc.)
        with their ICD-10 mappings.

        Args:
            procedure_code: IMO lexical code of the procedure (from normalize with domain="Procedure").

        Returns:
            Dict with procedure info and full list of associatedProblems with ICD-10 codes.
        """
        if not procedure_code or not procedure_code.strip():
            return {"success": False, "error": "procedure_code is required"}

        SIZE = 1000
        all_problems = []
        offset = 0
        lexical_base = None

        while True:
            query = f"""{{
  lexical(code: "{procedure_code.strip()}", domain: procedure) {{
    code
    title
    ... on ProcedureLexical {{
      numberOfAssociatedProblems
      associatedProblems(offset: {offset}, size: {SIZE}) {{
        code
        title
        ... on ProblemLexical {{
          mappings {{ code codeSystem }}
        }}
      }}
    }}
  }}
}}"""
            result = self._graphql_query(query, {})
            if not result.get("success") or not result.get("data"):
                return result

            lexical_data = result["data"].get("lexical")
            if not lexical_data:
                return {"success": True, "procedure": None, "associated_problems": []}

            if lexical_base is None:
                lexical_base = {
                    "code": lexical_data.get("code"),
                    "title": lexical_data.get("title"),
                    "numberOfAssociatedProblems": lexical_data.get("numberOfAssociatedProblems"),
                }

            page = lexical_data.get("associatedProblems", [])
            all_problems.extend(page)

            if len(page) < SIZE:
                break
            offset += SIZE

        problems_with_icd10 = []
        for p in all_problems:
            icd10_codes = [
                m["code"] for m in (p.get("mappings") or [])
                if m.get("codeSystem") == "icd10cm"
            ]
            problems_with_icd10.append({
                "code": p.get("code"),
                "title": p.get("title"),
                "icd10_codes": icd10_codes,
            })

        return {
            "success": True,
            "procedure": lexical_base,
            "associated_problems": problems_with_icd10,
        }
