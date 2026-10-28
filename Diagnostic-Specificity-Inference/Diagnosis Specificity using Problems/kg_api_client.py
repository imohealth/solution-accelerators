"""
Direct HTTP client for IMO Normalize API and Knowledge Graph (GOAT) GraphQL API.
Provides: normalize, get_lexical, get_allowed_refinements, get_narrower_sequential_refinements.
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

    # ─── Normalize API ──────────────────────────────────────────────────────

    def normalize_medical_term(self, input_term: str, domain: str = "Problem") -> Dict[str, Any]:
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

    def get_lexical(self, imo_lexical_code: str, domain: str = "Problem") -> Dict[str, Any]:
        gql_domain = domain.lower()
        SIZE = 1000

        query = f"""query GetLexical($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    synonyms {{ code title }}
    ... on ProblemLexical {{
      domainBroader(offset: 0, size: {SIZE}) {{ code title }}
      domainNarrower(offset: 0, size: {SIZE}) {{ code title }}
      mappings {{ code title codeSystem relationshipType }}
      appliedRefinements(offset: 0, size: {SIZE}) {{ code title group {{ code title }} }}
      allowedRefinements(offset: 0, size: {SIZE}) {{ code title group {{ code title }} }}
      refinementFamilies(offset: 0, size: {SIZE}) {{ code title lexicals {{ code title }} }}
    }}
  }}
}}"""

        variables = {"code": imo_lexical_code, "domain": gql_domain}
        result = self._graphql_query(query, variables)

        if not result.get("success") or not result.get("data"):
            return result

        lexical = result["data"].get("lexical")
        if not lexical:
            return {"success": True, "lexical": None}

        paginated_fields = ["domainBroader", "domainNarrower",
                            "appliedRefinements", "allowedRefinements", "refinementFamilies"]

        for field in paginated_fields:
            field_data = lexical.get(field)
            if not isinstance(field_data, list) or len(field_data) < SIZE:
                continue

            offset = SIZE
            while True:
                page_query = self._build_single_field_page_query(field, gql_domain, offset, SIZE)
                page_result = self._graphql_query(page_query, variables)

                if not page_result.get("success") or not page_result.get("data"):
                    break

                page_lexical = page_result["data"].get("lexical")
                if not page_lexical:
                    break

                page = page_lexical.get(field, [])
                lexical[field].extend(page)

                if len(page) < SIZE:
                    break
                offset += SIZE

        return {"success": True, "lexical": lexical}

    def _build_single_field_page_query(self, field: str, domain: str, offset: int, size: int) -> str:
        field_fragments = {
            "domainBroader": f"domainBroader(offset: {offset}, size: {size}) {{ code title }}",
            "domainNarrower": f"domainNarrower(offset: {offset}, size: {size}) {{ code title }}",
            "appliedRefinements": f"appliedRefinements(offset: {offset}, size: {size}) {{ code title group {{ code title }} }}",
            "allowedRefinements": f"allowedRefinements(offset: {offset}, size: {size}) {{ code title group {{ code title }} }}",
            "refinementFamilies": f"refinementFamilies(offset: {offset}, size: {size}) {{ code title lexicals {{ code title }} }}",
        }
        fragment = field_fragments[field]
        return f"""query GetLexical($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    ... on ProblemLexical {{
      {fragment}
    }}
  }}
}}"""

    def get_allowed_refinements(self, imo_lexical_code: str, domain: str = "Problem") -> Dict[str, Any]:
        gql_domain = domain.lower()
        SIZE = 1000
        all_refinements = []
        offset = 0
        lexical_base = None

        while True:
            query = f"""query GetAllowedRefinements($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    ... on ProblemLexical {{
      allowedRefinements(offset: {offset}, size: {SIZE}) {{ code title group {{ code title }} }}
    }}
  }}
}}"""
            variables = {"code": imo_lexical_code, "domain": gql_domain}
            result = self._graphql_query(query, variables)

            if not result.get("success") or not result.get("data"):
                return result

            lexical_data = result["data"].get("lexical")
            if not lexical_data:
                return {"success": True, "lexical": None}

            if lexical_base is None:
                lexical_base = {"code": lexical_data.get("code"), "title": lexical_data.get("title")}

            page = lexical_data.get("allowedRefinements", [])
            all_refinements.extend(page)

            if len(page) < SIZE:
                break
            offset += SIZE

        lexical_base["allowedRefinements"] = all_refinements
        return {"success": True, "lexical": lexical_base}

    def get_narrower_sequential_refinements(
        self,
        imo_lexical_code: str,
        refinement_sequence: List[List[str]],
        include_mappings: bool = False,
        domain: str = "Problem",
    ) -> Dict[str, Any]:
        gql_domain = domain.lower()
        SIZE = 1000

        steps = []
        for step in refinement_sequence:
            if isinstance(step, list):
                steps.append(step)
            else:
                steps.append([str(step)])

        if not steps:
            return {"success": False, "error": "No refinement steps provided"}

        MAX_STEPS_PER_QUERY = 3
        current_code = imo_lexical_code
        base_code = imo_lexical_code
        base_title = ""
        final_result = []

        for batch_start in range(0, len(steps), MAX_STEPS_PER_QUERY):
            batch = steps[batch_start:batch_start + MAX_STEPS_PER_QUERY]
            is_last_batch = (batch_start + MAX_STEPS_PER_QUERY) >= len(steps)

            query = self._build_refinement_query(batch, include_mappings=include_mappings and is_last_batch)

            variables = {"code": current_code, "domain": gql_domain}
            for i, step in enumerate(batch):
                variables[f"ref{i}"] = step

            result = self._graphql_query(query, variables)

            if not result.get("success"):
                return result

            lexical = result.get("data", {}).get("lexical")
            if not lexical:
                return {"success": True, "lexical": None}

            if not base_title:
                base_title = lexical.get("title", "")

            narrower_list = self._extract_deepest_narrower(lexical, len(batch))

            if not narrower_list:
                return {
                    "success": True,
                    "lexical": {
                        "code": base_code,
                        "title": base_title,
                        "refinementNarrower": [],
                    },
                }

            if is_last_batch:
                final_result = narrower_list
            else:
                current_code = narrower_list[0].get("code", "")
                if not current_code:
                    return {
                        "success": True,
                        "lexical": {
                            "code": base_code,
                            "title": base_title,
                            "refinementNarrower": narrower_list,
                        },
                    }

        return {
            "success": True,
            "lexical": {
                "code": base_code,
                "title": base_title,
                "refinementNarrower": final_result,
            },
        }

    def _build_refinement_query(self, steps: List[List[str]], include_mappings: bool = False) -> str:
        mappings_fragment = "mappings { code title codeSystem relationshipType }" if include_mappings else ""
        n = len(steps)

        inner = f"code title {mappings_fragment}"
        for i in range(n - 1, -1, -1):
            inner = f"refinementNarrower(refinements: $ref{i}, offset: 0, size: 1000) {{ {inner} }}"

        var_defs = ", ".join(f"$ref{i}: [String!]!" for i in range(n))

        return f"""query GetNarrowerSeqRef($code: String!, $domain: IMODomain!, {var_defs}) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    ... on ProblemLexical {{
      {inner}
    }}
  }}
}}"""

    def _extract_deepest_narrower(self, lexical: Dict, depth: int) -> List[Dict]:
        current = lexical
        for _ in range(depth):
            narrower = current.get("refinementNarrower", [])
            if not narrower:
                return []
            if isinstance(narrower[0], dict) and "refinementNarrower" in narrower[0]:
                current = narrower[0]
            else:
                return narrower
        return current.get("refinementNarrower", []) if isinstance(current, dict) else []
