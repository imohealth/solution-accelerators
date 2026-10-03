"""
Direct HTTP client for IMO Normalize API and Knowledge Graph (GOAT) GraphQL API.
Supports the Diagnosis Specificity Agent: normalize, get_lexical, allowedRefinements,
and nested refinementNarrower graph traversal.
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
                                    "title": item.get("title") or item.get("default_lexical_title") or "",
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

    def _graphql_query(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a GraphQL query against the GOAT KG API."""
        token = self._get_kg_token()
        if not token:
            return {"success": False, "error": "Failed to obtain KG API token"}

        try:
            response = requests.post(
                kg_config.KG_GRAPHQL_URL,
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
        """Get lexical concept from the KG with full relationship data.

        For problem domain: returns allowedRefinements, domainNarrower, mappings, etc.
        Uses pagination to fetch all results.
        """
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
    ... on MedicationLexical {{
      mappings {{ code title codeSystem relationshipType }}
      treatedProblems(offset: 0, size: {SIZE}) {{ code title }}
      causedProblems(offset: 0, size: {SIZE}) {{ code title }}
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

        paginated_fields = {
            "problem": ["domainBroader", "domainNarrower",
                        "appliedRefinements", "allowedRefinements", "refinementFamilies"],
            "medication": ["treatedProblems", "causedProblems"],
        }

        field_fragments = {
            "domainBroader": f"domainBroader(offset: {{offset}}, size: {SIZE}) {{ code title }}",
            "domainNarrower": f"domainNarrower(offset: {{offset}}, size: {SIZE}) {{ code title }}",
            "appliedRefinements": f"appliedRefinements(offset: {{offset}}, size: {SIZE}) {{ code title group {{ code title }} }}",
            "allowedRefinements": f"allowedRefinements(offset: {{offset}}, size: {SIZE}) {{ code title group {{ code title }} }}",
            "refinementFamilies": f"refinementFamilies(offset: {{offset}}, size: {SIZE}) {{ code title lexicals {{ code title }} }}",
            "treatedProblems": f"treatedProblems(offset: {{offset}}, size: {SIZE}) {{ code title }}",
            "causedProblems": f"causedProblems(offset: {{offset}}, size: {SIZE}) {{ code title }}",
        }

        type_map = {"problem": "ProblemLexical", "medication": "MedicationLexical"}
        type_name = type_map.get(gql_domain, "ProblemLexical")

        for field in paginated_fields.get(gql_domain, []):
            field_data = lexical.get(field)
            if not isinstance(field_data, list) or len(field_data) < SIZE:
                continue

            offset = SIZE
            while True:
                fragment = field_fragments[field].replace("{offset}", str(offset))
                page_query = f"""query GetLexical($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    ... on {type_name} {{
      {fragment}
    }}
  }}
}}"""
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

    def get_allowed_refinements(self, imo_lexical_code: str, domain: str = "Problem") -> Dict[str, Any]:
        """Get allowed refinements for a concept with pagination."""
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

    # ─── Nested Refinement Narrower Traversal ──────────────────────────────

    def _build_refinement_query(self, steps: List[List[str]], include_mappings: bool = True) -> str:
        """Build a nested refinementNarrower GraphQL query."""
        SIZE = 1000
        mappings_fragment = """
                    mappings { code title codeSystem relationshipType }""" if include_mappings else ""

        var_declarations = ["$code: String!", "$domain: IMODomain!"]
        for i in range(len(steps)):
            var_declarations.append(f"$ref{i}: [String!]")

        inner = f"""refinementNarrower(refinements: $ref{len(steps) - 1}, offset: 0, size: {SIZE}) {{
                  code
                  title
                  ... on ProblemLexical {{
                    appliedRefinements {{ code title }}
                    allowedRefinements(offset: 0, size: {SIZE}) {{ code title group {{ code title }} }}{mappings_fragment}
                  }}
                }}"""

        for i in range(len(steps) - 2, -1, -1):
            inner = f"""refinementNarrower(refinements: $ref{i}, offset: 0, size: {SIZE}) {{
                  code
                  title
                  ... on ProblemLexical {{
                    appliedRefinements {{ code title }}
                    {inner}
                  }}
                }}"""

        return f"""query GetRefinedNarrower({", ".join(var_declarations)}) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    ... on ProblemLexical {{
      {inner}
    }}
  }}
}}"""

    def _extract_deepest_narrower(self, lexical: Dict, num_steps: int) -> List[Dict]:
        """Traverse nested refinementNarrower response to get the deepest results."""
        current_list = lexical.get("refinementNarrower", [])
        for _ in range(num_steps - 1):
            if not current_list:
                break
            current_list = current_list[0].get("refinementNarrower", [])
        return current_list

    def _paginate_refinement_narrower(
        self, code: str, domain: str, refinements: List[str], size: int, include_mappings: bool = True
    ) -> List[Dict]:
        """Fetch remaining pages of refinementNarrower when first page hit SIZE."""
        mappings_fragment = """
                    mappings { code title codeSystem relationshipType }""" if include_mappings else ""
        all_extra = []
        offset = size
        refinements_arg = ", ".join(f'"{r}"' for r in refinements)
        while True:
            query = f"""query GetRefinementPage($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    ... on ProblemLexical {{
      refinementNarrower(refinements: [{refinements_arg}], offset: {offset}, size: {size}) {{
        code
        title
        ... on ProblemLexical {{
          appliedRefinements {{ code title }}
          allowedRefinements(offset: 0, size: {size}) {{ code title group {{ code title }} }}{mappings_fragment}
        }}
      }}
    }}
  }}
}}"""
            result = self._graphql_query(query, {"code": code, "domain": domain})
            if not result.get("success"):
                break
            lexical = result.get("data", {}).get("lexical")
            if not lexical:
                break
            page = lexical.get("refinementNarrower", [])
            all_extra.extend(page)
            if len(page) < size:
                break
            offset += size
        return all_extra

    def get_narrower_sequential_refinements(
        self,
        imo_lexical_code: str,
        refinement_sequence: List[List[str]],
        include_mappings: bool = True,
        domain: str = "Problem",
    ) -> Dict[str, Any]:
        """Apply refinements sequentially to resolve the most specific concept.

        Batches in groups of 3 to stay within query depth limits.
        """
        SIZE = 1000
        gql_domain = domain.lower()

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

            if len(narrower_list) >= SIZE and is_last_batch:
                last_refinements = batch[-1]
                extra = self._paginate_refinement_narrower(
                    current_code, gql_domain, last_refinements, SIZE,
                    include_mappings=include_mappings,
                )
                narrower_list.extend(extra)

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
