"""
Direct HTTP client for IMO Normalize API and Knowledge Graph (GOAT) GraphQL API.
Supports two-phase diagnosis refinement: medication-guided drill-down + note-driven refinement axes.
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

    # --- Normalize API ---

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

    # --- Knowledge Graph (GOAT) GraphQL API ---

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

    def get_lexical(self, imo_lexical_code: str, domain: str = "Problem") -> Dict[str, Any]:
        """
        Get lexical concept from the Knowledge Graph with full relationship data.

        For medication domain: returns treatedProblems, causedProblems.
        For problem domain: returns allowedRefinements, associatedTreatments, etc.

        Uses offset/size pagination on all list fields.
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
    ... on ProcedureLexical {{
      mappings {{ code title codeSystem relationshipType }}
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
            "procedure": [],
        }

        fields_to_check = paginated_fields.get(gql_domain, [])

        for field in fields_to_check:
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
        """Build a query to fetch a single paginated field at a given offset."""
        field_fragments = {
            "domainBroader": f"domainBroader(offset: {offset}, size: {size}) {{ code title }}",
            "domainNarrower": f"domainNarrower(offset: {offset}, size: {size}) {{ code title }}",
            "appliedRefinements": f"appliedRefinements(offset: {offset}, size: {size}) {{ code title group {{ code title }} }}",
            "allowedRefinements": f"allowedRefinements(offset: {offset}, size: {size}) {{ code title group {{ code title }} }}",
            "refinementFamilies": f"refinementFamilies(offset: {offset}, size: {size}) {{ code title lexicals {{ code title }} }}",
            "treatedProblems": f"treatedProblems(offset: {offset}, size: {size}) {{ code title }}",
            "causedProblems": f"causedProblems(offset: {offset}, size: {size}) {{ code title }}",
        }

        fragment = field_fragments[field]

        if domain == "medication":
            return f"""query GetLexical($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    ... on MedicationLexical {{
      {fragment}
    }}
  }}
}}"""
        elif domain == "procedure":
            return f"""query GetLexical($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    ... on ProcedureLexical {{
      {fragment}
    }}
  }}
}}"""
        else:
            return f"""query GetLexical($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    ... on ProblemLexical {{
      {fragment}
    }}
  }}
}}"""

    def get_domain_hierarchy(self, imo_lexical_code: str, direction: str = "narrower", domain: str = "Problem") -> Dict[str, Any]:
        """
        Get domain hierarchy (children or parents) for a concept.

        Uses offset/size pagination on domainNarrower/domainBroader.
        """
        gql_domain = domain.lower()
        SIZE = 1000
        hierarchy_field = "domainBroader" if direction == "broader" else "domainNarrower"

        if direction == "broader":
            query = f"""query GetDomainBroader($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    synonyms {{ code title }}
    ... on ProblemLexical {{
      domainBroader(offset: 0, size: {SIZE}) {{ code title }}
    }}
  }}
}}"""
        else:
            query = f"""query GetDomainNarrower($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    synonyms {{ code title }}
    ... on ProblemLexical {{
      domainNarrower(offset: 0, size: {SIZE}) {{ code title }}
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

        hierarchy_data = lexical.get(hierarchy_field, [])
        if isinstance(hierarchy_data, list) and len(hierarchy_data) >= SIZE:
            offset = SIZE
            while True:
                page_query = f"""query GetDomainHierarchyPage($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    ... on ProblemLexical {{
      {hierarchy_field}(offset: {offset}, size: {SIZE}) {{ code title }}
    }}
  }}
}}"""
                page_result = self._graphql_query(page_query, variables)

                if not page_result.get("success") or not page_result.get("data"):
                    break

                page_lexical = page_result["data"].get("lexical")
                if not page_lexical:
                    break

                page = page_lexical.get(hierarchy_field, [])
                lexical[hierarchy_field].extend(page)

                if len(page) < SIZE:
                    break
                offset += SIZE

        return {"success": True, "lexical": lexical}

    def get_treatments_for_problem(self, imo_lexical_code: str) -> Dict[str, Any]:
        """Get treatment-related medications for a problem from the KG."""
        SIZE = 1000
        variables = {"code": imo_lexical_code, "domain": "problem"}
        all_associated = []
        all_supportive = []
        lexical_base = None

        offset = 0
        while True:
            query = f"""query GetTreatments($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    ... on ProblemLexical {{
      numberOfAssociatedTreatments
      numberOfSupportiveTreatments
      associatedTreatments(offset: {offset}, size: {SIZE}) {{ ... on Lexical {{ code title }} ... on MedicationLexical {{ code title }} }}
    }}
  }}
}}"""
            result = self._graphql_query(query, variables)
            if not result.get("success") or not result.get("data"):
                return result

            lexical_data = result["data"].get("lexical")
            if not lexical_data:
                return {"success": True, "lexical": None}

            if lexical_base is None:
                lexical_base = {
                    "code": lexical_data.get("code"),
                    "title": lexical_data.get("title"),
                    "numberOfAssociatedTreatments": lexical_data.get("numberOfAssociatedTreatments"),
                    "numberOfSupportiveTreatments": lexical_data.get("numberOfSupportiveTreatments"),
                }

            page = lexical_data.get("associatedTreatments", [])
            all_associated.extend(page)

            if len(page) < SIZE:
                break
            offset += SIZE

        offset = 0
        while True:
            query = f"""query GetTreatments($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    ... on ProblemLexical {{
      supportiveTreatments(offset: {offset}, size: {SIZE}) {{ code title }}
    }}
  }}
}}"""
            result = self._graphql_query(query, variables)
            if not result.get("success") or not result.get("data"):
                break

            lexical_data = result["data"].get("lexical")
            if not lexical_data:
                break

            page = lexical_data.get("supportiveTreatments", [])
            all_supportive.extend(page)

            if len(page) < SIZE:
                break
            offset += SIZE

        lexical_base["associatedTreatments"] = all_associated
        lexical_base["supportiveTreatments"] = all_supportive
        return {"success": True, "lexical": lexical_base}

    def get_caused_problems(self, imo_lexical_code: str, domain: str = "Problem") -> Dict[str, Any]:
        """Get problems caused by a condition or medication."""
        SIZE = 1000
        gql_domain = domain.lower()
        variables = {"code": imo_lexical_code, "domain": gql_domain}
        all_caused = []
        all_causative = []
        lexical_base = None

        offset = 0
        while True:
            if gql_domain == "medication":
                query = f"""query GetCausedProblems($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    ... on MedicationLexical {{
      numberOfCausedProblems
      causedProblems(offset: {offset}, size: {SIZE}) {{ code title }}
    }}
  }}
}}"""
            else:
                query = f"""query GetCausedProblems($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    ... on ProblemLexical {{
      numberOfCausedProblems
      numberOfCausativeAgents
      causedProblems(offset: {offset}, size: {SIZE}) {{ code title }}
    }}
  }}
}}"""

            result = self._graphql_query(query, variables)
            if not result.get("success") or not result.get("data"):
                return result

            lexical_data = result["data"].get("lexical")
            if not lexical_data:
                return {"success": True, "lexical": None}

            if lexical_base is None:
                lexical_base = {
                    "code": lexical_data.get("code"),
                    "title": lexical_data.get("title"),
                }

            page = lexical_data.get("causedProblems", [])
            all_caused.extend(page)

            if len(page) < SIZE:
                break
            offset += SIZE

        lexical_base["causedProblems"] = all_caused

        if gql_domain != "medication":
            offset = 0
            while True:
                query = f"""query GetCausedProblems($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    ... on ProblemLexical {{
      causativeAgents(offset: {offset}, size: {SIZE}) {{ ... on MedicationLexical {{ code title }} }}
    }}
  }}
}}"""
                result = self._graphql_query(query, variables)
                if not result.get("success") or not result.get("data"):
                    break

                lexical_data = result["data"].get("lexical")
                if not lexical_data:
                    break

                page = lexical_data.get("causativeAgents", [])
                all_causative.extend(page)

                if len(page) < SIZE:
                    break
                offset += SIZE

            lexical_base["causativeAgents"] = all_causative

        return {"success": True, "lexical": lexical_base}

    def get_diagnostics_for_problem(self, imo_lexical_code: str) -> Dict[str, Any]:
        """Get diagnostic tests and lab procedures for a problem."""
        SIZE = 1000
        variables = {"code": imo_lexical_code, "domain": "problem"}
        all_procedures = []
        lexical_base = None

        offset = 0
        while True:
            query = f"""query GetDiagnostics($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    ... on ProblemLexical {{
      numberOfAssociatedProcedures
      associatedProcedures(offset: {offset}, size: {SIZE}) {{ code title }}
    }}
  }}
}}"""
            result = self._graphql_query(query, variables)
            if not result.get("success") or not result.get("data"):
                return result

            lexical_data = result["data"].get("lexical")
            if not lexical_data:
                return {"success": True, "lexical": None}

            if lexical_base is None:
                lexical_base = {
                    "code": lexical_data.get("code"),
                    "title": lexical_data.get("title"),
                    "numberOfAssociatedProcedures": lexical_data.get("numberOfAssociatedProcedures"),
                }

            page = lexical_data.get("associatedProcedures", [])
            all_procedures.extend(page)

            if len(page) < SIZE:
                break
            offset += SIZE

        lexical_base["associatedProcedures"] = all_procedures
        return {"success": True, "lexical": lexical_base}

    def get_medication_diagnosis_proto(
        self,
        diagnosis_code: str,
        medication_codes: List[str],
    ) -> Dict[str, Any]:
        """
        KG lookup: return narrower problem concepts of a base diagnosis that
        have ties to the supplied medication codes, via the
        `domainNarrowerByMedications` field on ProblemLexical.

        Uses offset/size pagination on domainNarrowerByMedications.
        """
        if not diagnosis_code:
            return {"success": False, "error": "diagnosis_code is required"}
        if not medication_codes:
            return {"success": False, "error": "medication_codes list is empty"}

        SIZE = 1000
        medications_arg = ", ".join(f'"{c}"' for c in medication_codes if c)
        all_narrower = []
        lexical_base = None
        offset = 0

        while True:
            query = f"""{{
  lexical(code: "{diagnosis_code}", domain: problem) {{
    title
    ... on ProblemLexical {{
      domainNarrowerByMedications(medications: [{medications_arg}], offset: {offset}, size: {SIZE}) {{
        code
        title
        ... on ProblemLexical {{
          numberOfDomainChildren
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
                return {"success": True, "lexical": None}

            if lexical_base is None:
                lexical_base = {
                    "title": lexical_data.get("title"),
                }

            page = lexical_data.get("domainNarrowerByMedications", [])
            all_narrower.extend(page)

            if len(page) < SIZE:
                break
            offset += SIZE

        lexical_base["domainNarrowerByMedications"] = all_narrower
        return {"success": True, "lexical": lexical_base}

    def get_allowed_refinements(self, imo_lexical_code: str, domain: str = "Problem") -> Dict[str, Any]:
        """
        Get allowed refinements for a concept. Returns refinement groups
        (type, laterality, severity, chronicity, etc.) that can narrow a diagnosis.

        Uses offset/size pagination on allowedRefinements.
        """
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

    # --- Sequential Refinement helpers ---

    def _build_refinement_query(self, steps: List[List[str]], include_mappings: bool = True) -> str:
        """Build a nested refinementNarrower GraphQL query for the given steps."""
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
        """Fetch remaining pages of refinementNarrower when the first page hit SIZE."""
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
        """
        Get narrower concepts by applying refinements sequentially.
        Uses nested refinementNarrower calls. Batches in groups of 3 to stay
        within query depth limit of 7.

        Args:
            imo_lexical_code: Base concept lexical code
            refinement_sequence: Array of arrays - each inner array is one refinement step
            include_mappings: Whether to include ICD-10/code mappings
            domain: IMO domain
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
