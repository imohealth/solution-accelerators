"""
Direct HTTP client for IMO Normalize API and Knowledge Graph (GOAT) GraphQL API.
Provides: normalize_medical_term, find_diagnosis_by_procedure.
"""

import time
import uuid
import requests
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    def normalize_medical_term(self, input_term: str, domain: str = "Problem", order_name: str = "") -> Dict[str, Any]:
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

    # --- Hierarchy Traversal for Diagnosis Inference by Procedure ---

    def find_diagnosis_by_procedure(
        self,
        diagnosis_code: str,
        procedure_codes: List[str],
        max_depth: int = 5,
    ) -> Dict[str, Any]:
        """
        Recursively traverse the full domainNarrower hierarchy of a base diagnosis,
        checking each node's treatmentProcedures, evaluationProcedures, and
        preventiveProcedures for matches against the given procedure codes.

        Uses paginated 3-level nested queries to traverse the entire tree efficiently,
        then checks procedures concurrently with ThreadPoolExecutor.
        """
        if not diagnosis_code:
            return {"success": False, "error": "diagnosis_code is required"}
        if not procedure_codes:
            return {"success": False, "error": "procedure_codes list is empty"}

        proc_set = set(str(c).strip() for c in procedure_codes if c)
        PAGE_SIZE = 1000

        base_query = f"""{{
  lexical(code: "{diagnosis_code}", domain: problem) {{
    code
    title
  }}
}}"""
        base_result = self._graphql_query(base_query, {})
        if not base_result.get("success"):
            return base_result
        base_lexical = (base_result.get("data") or {}).get("lexical")
        if not base_lexical:
            return {"success": False, "error": f"No concept found for code {diagnosis_code}"}
        base_title = base_lexical.get("title", "")

        all_codes: List[str] = []
        icd10_map: Dict[str, List[Dict]] = {}
        queue: List[tuple] = [(diagnosis_code, 0)]
        explored: set = set()
        traversal_queries = 0

        while queue:
            current_code, start_offset = queue.pop(0)
            explore_key = f"{current_code}:{start_offset}"
            if explore_key in explored:
                continue
            explored.add(explore_key)

            offset = start_offset
            while True:
                query = self._build_proc_narrower_query(current_code, PAGE_SIZE, offset, max_depth)
                result = self._graphql_query(query, {})
                traversal_queries += 1

                if not result.get("success"):
                    break

                lexical = (result.get("data") or {}).get("lexical")
                if not lexical:
                    break

                l1_nodes = lexical.get("domainNarrower", [])
                if not l1_nodes:
                    break

                pending: List[tuple] = []
                self._collect_codes_from_tree(l1_nodes, 1, all_codes, icd10_map, pending, PAGE_SIZE, max_depth)

                for item in pending:
                    queue.append(item)

                if len(l1_nodes) < PAGE_SIZE:
                    break
                offset += PAGE_SIZE

        unique_codes = list(dict.fromkeys(all_codes))

        matched_nodes = []
        proc_queries = 0

        def _check_proc(code):
            q = f"""{{
  lexical(code: "{code}", domain: problem) {{
    code
    title
    ... on ProblemLexical {{
      treatmentProcedures {{ code title }}
      evaluationProcedures {{ code title }}
      preventiveProcedures {{ code title }}
    }}
  }}
}}"""
            return self._graphql_query(q, {})

        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = {pool.submit(_check_proc, c): c for c in unique_codes}
            for future in as_completed(futures):
                proc_queries += 1
                r = future.result()
                if not r.get("success"):
                    continue
                lex = (r.get("data") or {}).get("lexical")
                if not lex:
                    continue
                matched_procs = []
                for field in ("evaluationProcedures", "treatmentProcedures", "preventiveProcedures"):
                    for p in lex.get(field) or []:
                        if p.get("code") in proc_set:
                            matched_procs.append({
                                "code": p["code"],
                                "title": p.get("title", ""),
                                "category": field.replace("Procedures", ""),
                            })
                if matched_procs:
                    node_code = lex.get("code", futures[future])
                    matched_nodes.append({
                        "code": node_code,
                        "title": lex.get("title", ""),
                        "icd10_codes": icd10_map.get(node_code, []),
                        "matched_procedures": matched_procs,
                    })

        return {
            "success": True,
            "base": {"code": diagnosis_code, "title": base_title},
            "matched_nodes": matched_nodes,
            "stats": {
                "total_nodes_traversed": len(unique_codes),
                "nodes_with_matching_procedure": len(matched_nodes),
                "traversal_queries": traversal_queries,
                "procedure_queries": proc_queries,
                "total_queries": traversal_queries + proc_queries,
            },
        }

    def _build_proc_narrower_query(self, code: str, size: int, offset: int, max_depth: int) -> str:
        inner = """
                code
                title
                ... on ProblemLexical {
                  numberOfDomainChildren
                  mappings { code title codeSystem }
                }"""
        levels = min(3, max_depth)
        q = inner
        for _ in range(levels - 1):
            q = f"""
                code
                title
                ... on ProblemLexical {{
                  numberOfDomainChildren
                  mappings {{ code title codeSystem }}
                  domainNarrower(size: {size}, offset: 0) {{{q}
                  }}
                }}"""

        return f"""{{
  lexical(code: "{code}", domain: problem) {{
    code
    title
    ... on ProblemLexical {{
      domainNarrower(size: {size}, offset: {offset}) {{{q}
      }}
    }}
  }}
}}"""

    def _collect_codes_from_tree(
        self, nodes: List[Dict], depth: int, collected: List[str],
        mappings_map: Dict[str, List[Dict]],
        pending: List[tuple], page_size: int, max_depth: int
    ) -> None:
        for node in nodes or []:
            code = node.get("code", "")
            if code:
                collected.append(code)
                icd10 = [
                    {"code": m["code"], "title": m.get("title", "")}
                    for m in node.get("mappings") or []
                    if m.get("code") and m.get("codeSystem") == "icd10cm"
                ]
                if icd10:
                    mappings_map[code] = icd10

            children = node.get("domainNarrower", [])
            num_children = node.get("numberOfDomainChildren", 0)

            if children:
                self._collect_codes_from_tree(children, depth + 1, collected, mappings_map, pending, page_size, max_depth)
                if len(children) >= page_size and len(children) < num_children:
                    pending.append((code, page_size))
            elif num_children and num_children > 0 and depth < max_depth:
                pending.append((code, 0))
