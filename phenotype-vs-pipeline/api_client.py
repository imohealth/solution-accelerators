"""
Client for IMO Normalize API and Knowledge Graph (GOAT) GraphQL API.
Handles OAuth2 token management for both APIs with separate credentials.
"""

import logging
import threading
import time
import uuid
import requests
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import config

logger = logging.getLogger(__name__)


# ── Data classes ───────────────────────────────────────────────────────

@dataclass
class NormalizedCode:
    input_term: str = ""
    source_column: str = ""
    domain: str = ""
    imo_code: str = ""
    imo_title: str = ""
    lexical_code: str = ""
    concept_code: str = ""
    score: float = 0.0
    icd10cm_code: str = ""
    icd10cm_title: str = ""
    snomed_code: str = ""
    snomed_title: str = ""
    icd9cm_code: str = ""
    icd9cm_title: str = ""
    cpt_codes: List[Dict] = field(default_factory=list)
    icd10pcs_codes: List[Dict] = field(default_factory=list)
    hcpcs_code: str = ""
    hcpcs_title: str = ""
    loinc_code: str = ""
    loinc_title: str = ""
    umls_codes: List[Dict] = field(default_factory=list)
    rxnorm_code: str = ""
    rxnorm_title: str = ""
    ndc_codes: List[Dict] = field(default_factory=list)

    @property
    def cpt_codes_str(self) -> str:
        return ", ".join(c["code"] for c in self.cpt_codes) if self.cpt_codes else ""

    @property
    def cpt_titles_str(self) -> str:
        return " | ".join(c["title"] for c in self.cpt_codes) if self.cpt_codes else ""

    @property
    def icd10pcs_codes_str(self) -> str:
        return ", ".join(c["code"] for c in self.icd10pcs_codes) if self.icd10pcs_codes else ""

    @property
    def icd10pcs_titles_str(self) -> str:
        return " | ".join(c["title"] for c in self.icd10pcs_codes) if self.icd10pcs_codes else ""

    @property
    def umls_codes_str(self) -> str:
        return ", ".join(c["code"] for c in self.umls_codes) if self.umls_codes else ""


@dataclass
class ExpandedCode:
    parent_input_term: str = ""
    parent_imo_code: str = ""
    parent_title: str = ""
    parent_lexical_code: str = ""
    domain: str = ""
    relationship: str = "domainNarrower"
    narrower_lexical_code: str = ""
    narrower_title: str = ""
    kg_level: int = 0
    kg_parent_code: str = ""
    kg_parent_title: str = ""
    icd10cm_codes: List[Dict] = field(default_factory=list)
    snomed_codes: List[Dict] = field(default_factory=list)
    icd9cm_codes: List[Dict] = field(default_factory=list)
    cpt_codes: List[Dict] = field(default_factory=list)
    icd10pcs_codes: List[Dict] = field(default_factory=list)
    hcpcs_codes: List[Dict] = field(default_factory=list)
    loinc_codes: List[Dict] = field(default_factory=list)
    rxnorm_codes: List[Dict] = field(default_factory=list)

    @property
    def icd10cm_codes_str(self) -> str:
        return ", ".join(c["code"] for c in self.icd10cm_codes) if self.icd10cm_codes else ""

    @property
    def icd10cm_titles_str(self) -> str:
        return " | ".join(c["title"] for c in self.icd10cm_codes) if self.icd10cm_codes else ""

    @property
    def snomed_codes_str(self) -> str:
        return ", ".join(c["code"] for c in self.snomed_codes) if self.snomed_codes else ""

    @property
    def snomed_titles_str(self) -> str:
        return " | ".join(c["title"] for c in self.snomed_codes) if self.snomed_codes else ""

    @property
    def icd9cm_codes_str(self) -> str:
        return ", ".join(c["code"] for c in self.icd9cm_codes) if self.icd9cm_codes else ""

    @property
    def icd9cm_titles_str(self) -> str:
        return " | ".join(c["title"] for c in self.icd9cm_codes) if self.icd9cm_codes else ""

    @property
    def cpt_codes_str(self) -> str:
        return ", ".join(c["code"] for c in self.cpt_codes) if self.cpt_codes else ""

    @property
    def cpt_titles_str(self) -> str:
        return " | ".join(c["title"] for c in self.cpt_codes) if self.cpt_codes else ""

    @property
    def icd10pcs_codes_str(self) -> str:
        return ", ".join(c["code"] for c in self.icd10pcs_codes) if self.icd10pcs_codes else ""

    @property
    def icd10pcs_titles_str(self) -> str:
        return " | ".join(c["title"] for c in self.icd10pcs_codes) if self.icd10pcs_codes else ""

    @property
    def hcpcs_codes_str(self) -> str:
        return ", ".join(c["code"] for c in self.hcpcs_codes) if self.hcpcs_codes else ""

    @property
    def hcpcs_titles_str(self) -> str:
        return " | ".join(c["title"] for c in self.hcpcs_codes) if self.hcpcs_codes else ""

    @property
    def loinc_codes_str(self) -> str:
        return ", ".join(c["code"] for c in self.loinc_codes) if self.loinc_codes else ""

    @property
    def loinc_titles_str(self) -> str:
        return " | ".join(c["title"] for c in self.loinc_codes) if self.loinc_codes else ""

    @property
    def rxnorm_codes_str(self) -> str:
        return ", ".join(c["code"] for c in self.rxnorm_codes) if self.rxnorm_codes else ""

    @property
    def rxnorm_titles_str(self) -> str:
        return " | ".join(c["title"] for c in self.rxnorm_codes) if self.rxnorm_codes else ""

    @property
    def relationship_types(self) -> str:
        all_maps = (self.icd10cm_codes + self.snomed_codes + self.icd9cm_codes +
                    self.cpt_codes + self.icd10pcs_codes + self.hcpcs_codes + self.loinc_codes + self.rxnorm_codes)
        types = set(m.get("relationshipType", "") for m in all_maps if m.get("relationshipType"))
        return ", ".join(types) if types else ""


# ── API Client ─────────────────────────────────────────────────────────

class ApiClient:
    """Client for IMO Normalize + Knowledge Graph APIs with token caching."""

    def __init__(self):
        self._normalize_token: Optional[str] = None
        self._normalize_token_expiry: float = 0
        self._kg_token: Optional[str] = None
        self._kg_token_expiry: float = 0
        self._normalize_lock = threading.Lock()
        self._kg_lock = threading.Lock()

    # ── OAuth ──────────────────────────────────────────────────────────

    def _get_oauth_token(
        self,
        client_id: str,
        client_secret: str,
        audience: str,
        auth_url: str,
    ) -> Optional[str]:
        """Get OAuth2 token using client credentials grant."""
        try:
            response = requests.post(
                auth_url,
                headers={"Content-Type": "application/json"},
                json={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "audience": audience,
                },
                timeout=30,
            )
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                logger.error("OAuth error: %s - %s", response.status_code, response.text[:200])
                return None
        except Exception as e:
            logger.error("OAuth exception: %s", e)
            return None

    def _get_normalize_token(self) -> Optional[str]:
        """Get cached or fresh Normalize API token (thread-safe)."""
        with self._normalize_lock:
            if self._normalize_token and time.time() < self._normalize_token_expiry:
                return self._normalize_token
            token = self._get_oauth_token(
                config.IMO_NORMALIZE_CLIENT_ID,
                config.IMO_NORMALIZE_CLIENT_SECRET,
                config.IMO_AUDIENCE,
                config.IMO_AUTH_URL,
            )
            if token:
                self._normalize_token = token
                self._normalize_token_expiry = time.time() + 3540
                logger.info("Normalize token obtained")
            return token

    def _get_kg_token(self) -> Optional[str]:
        """Get cached or fresh KG/GOAT API token (sandbox, thread-safe)."""
        with self._kg_lock:
            if self._kg_token and time.time() < self._kg_token_expiry:
                return self._kg_token
            token = self._get_oauth_token(
                config.IMO_KG_CLIENT_ID,
                config.IMO_KG_CLIENT_SECRET,
                config.KG_AUDIENCE,
                config.KG_AUTH_URL,
            )
            if token:
                self._kg_token = token
                self._kg_token_expiry = time.time() + 3540
                logger.info("KG token obtained")
            return token

    # ── Normalize API ──────────────────────────────────────────────────

    def normalize(self, input_term: str, domain: str = "Problem") -> Dict[str, Any]:
        """Normalize a medical term using IMO Precision Normalize API."""
        token = self._get_normalize_token()
        if not token:
            return {"success": False, "input_term": input_term, "matches": []}

        payload = {
            "organization_id": "IMO",
            "client_request_id": str(uuid.uuid4()),
            "preferences": {
                "threshold": 0.0,
                "match_field_pref": "input_term",
                "debug": True,
                "size": config.NORMALIZE_TOP_N,
            },
            "requests": [{
                "record_id": str(uuid.uuid4()),
                "domain": domain.lower(),
                "input_term": input_term,
            }],
        }

        try:
            response = requests.post(
                config.IMO_NORMALIZE_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            req_list = data.get("requests", [])
            if not req_list:
                return {"success": False, "input_term": input_term, "matches": []}
            items = req_list[0].get("response", {}).get("items", [])
            return {"success": len(items) > 0, "input_term": input_term, "matches": items}
        except Exception as e:
            logger.error("Normalize API error for '%s': %s", input_term, e)
            return {"success": False, "input_term": input_term, "matches": []}

    def extract_all_codes(self, item: Dict, input_term: str, domain: str, source_column: str) -> NormalizedCode:
        """Extract all code systems from a single Normalize API match."""

        def _get_codes(mappings: Dict, system: str) -> List[Dict]:
            entry = mappings.get(system, {})
            if not entry or not isinstance(entry, dict):
                return []
            codes = entry.get("codes", [])
            if not isinstance(codes, list):
                return []
            return [{"code": c.get("code", ""), "title": c.get("title", "")} for c in codes if c.get("code")]

        def _first(code_list: List[Dict], key: str, default="") -> str:
            return code_list[0].get(key, default) if code_list else default

        mappings = item.get("metadata", {}).get("mappings", {})

        icd10cm_list = _get_codes(mappings, "icd10cm")
        snomed_list = _get_codes(mappings, "snomedInternational")
        icd9cm_list = _get_codes(mappings, "icd9cm")
        cpt_list = _get_codes(mappings, "cpt")
        pcs_list = _get_codes(mappings, "icd10pcs")
        hcpcs_list = _get_codes(mappings, "hcpcs")
        loinc_list = _get_codes(mappings, "loinc")
        umls_list = _get_codes(mappings, "umls")

        # rxnorm uses rxnorm_code key (not code); title is in rxnorm_titles[0].title
        rxnorm_entry = mappings.get("rxnorm", {})
        rxnorm_list = []
        if rxnorm_entry and isinstance(rxnorm_entry, dict):
            for c in rxnorm_entry.get("codes", []):
                rxc = c.get("rxnorm_code", "")
                if rxc:
                    titles = c.get("rxnorm_titles", [])
                    title = titles[0].get("title", "") if titles else ""
                    rxnorm_list.append({"code": str(rxc), "title": title})

        # ndc uses ndc_code key; title from ndc_metadata brand_name or generic_name
        ndc_entry = mappings.get("ndc", {})
        ndc_list = []
        if ndc_entry and isinstance(ndc_entry, dict):
            for c in ndc_entry.get("codes", []):
                ndc_code = c.get("ndc_code", "")
                if ndc_code:
                    meta = (c.get("ndc_metadata") or [{}])[0]
                    title = meta.get("brand_name") or meta.get("generic_name", "")
                    ndc_list.append({"code": ndc_code, "title": title})

        return NormalizedCode(
            input_term=input_term,
            source_column=source_column,
            domain=domain,
            imo_code=str(item.get("code", "")),
            imo_title=item.get("title", ""),
            lexical_code=str(item.get("lexical_code", "")),
            concept_code=str(item.get("concept_code", "")),
            score=item.get("score", 0.0),
            icd10cm_code=_first(icd10cm_list, "code"),
            icd10cm_title=_first(icd10cm_list, "title"),
            snomed_code=_first(snomed_list, "code"),
            snomed_title=_first(snomed_list, "title"),
            icd9cm_code=_first(icd9cm_list, "code"),
            icd9cm_title=_first(icd9cm_list, "title"),
            cpt_codes=cpt_list,
            icd10pcs_codes=pcs_list,
            hcpcs_code=_first(hcpcs_list, "code"),
            hcpcs_title=_first(hcpcs_list, "title"),
            loinc_code=_first(loinc_list, "code"),
            loinc_title=_first(loinc_list, "title"),
            umls_codes=umls_list,
            rxnorm_code=_first(rxnorm_list, "code"),
            rxnorm_title=_first(rxnorm_list, "title"),
            ndc_codes=ndc_list,
        )

    def normalize_and_extract(self, term: str, domain: str, source_column: str) -> Optional[NormalizedCode]:
        """Normalize + extract in one call."""
        result = self.normalize(term, domain)
        if not result["success"] or not result["matches"]:
            logger.warning("No match for '%s' [%s]", term, domain)
            return None
        return self.extract_all_codes(result["matches"][0], term, domain, source_column)

    # ── Knowledge Graph API ────────────────────────────────────────────

    def _graphql(self, query: str, variables: Dict) -> Dict[str, Any]:
        """Execute a GraphQL query against KG GOAT API with retry on 500/SSL/connection errors."""
        token = self._get_kg_token()
        if not token:
            return {"success": False, "error": "Failed to obtain KG token"}

        _RETRYABLE = (
            requests.exceptions.SSLError,
            requests.exceptions.ConnectionError,
        )

        last_error = "Unknown error"
        max_attempts = 3
        for attempt in range(max_attempts):
            if attempt > 0:
                wait = 5 * (2 ** (attempt - 1))  # 5s, 10s
                logger.warning("KG transient error, retrying in %ds (attempt %d/%d): %s", wait, attempt + 1, max_attempts, last_error)
                time.sleep(wait)
            try:
                response = requests.post(
                    config.KG_GRAPHQL_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"query": query, "variables": variables},
                    timeout=60,
                )
                if response.status_code == 500:
                    last_error = f"500 Server Error for url: {config.KG_GRAPHQL_URL}"
                    continue
                response.raise_for_status()
                result = response.json()
                if "errors" in result:
                    logger.warning("GraphQL errors: %s", result["errors"])
                    return {"success": False, "error": "; ".join(e.get("message", "") for e in result["errors"])}
                return {"success": True, "data": result.get("data", {})}
            except _RETRYABLE as e:
                last_error = str(e)
                # SSL/connection drops are transient — retry
                continue
            except Exception as e:
                last_error = str(e)
                if not isinstance(e, requests.exceptions.HTTPError):
                    break

        logger.error("GraphQL error: %s", last_error)
        return {"success": False, "error": last_error}

    def _build_nested_query(self, fragment: str, l1_offset: int = 0, size: int = 250) -> str:
        """Build 3-level nested domainNarrower query with L1 pagination."""
        return f"""query GetNestedNarrower($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    ... on {fragment} {{
      domainNarrower(offset: {l1_offset}, size: {size}) {{
        code
        title
        ... on {fragment} {{
          mappings {{ code title codeSystem relationshipType }}
          domainNarrower(offset: 0, size: {size}) {{
            code
            title
            ... on {fragment} {{
              mappings {{ code title codeSystem relationshipType }}
              domainNarrower(offset: 0, size: {size}) {{
                code
                title
                ... on {fragment} {{
                  mappings {{ code title codeSystem relationshipType }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
  }}
}}"""

    def _fetch_3_levels(self, lexical_code: str, domain: str, fragment: str,
                        label: str = "", base_level: int = 0,
                        root_code: str = "", root_title: str = "") -> tuple:
        """Fetch 3 levels with L1 pagination. Returns (all_items, l3_codes, l3_titles, l1, l2, l3 counts, api_failed).
        api_failed=True when the first API call returned a non-success response (e.g. 500 error);
        in that case the empty result must NOT be cached as it does not reflect the real KG state."""
        SIZE = 250
        gql_domain = domain.lower()
        all_narrower = []
        l3_codes = []
        l3_titles = {}
        l1_total = 0
        l2_total = 0
        l3_total = 0
        offset = 0
        page = 1
        api_failed = False
        parent_code_for_l1 = root_code or lexical_code

        while True:
            query = self._build_nested_query(fragment, offset, SIZE)
            result = self._graphql(query, {"code": lexical_code, "domain": gql_domain})
            if not result.get("success") or not result.get("data"):
                if page == 1:
                    api_failed = True  # first call failed — treat result as unreliable
                break
            lexical = result["data"].get("lexical")
            if not lexical:
                break

            l1_items = lexical.get("domainNarrower", [])
            if label and page > 1:
                print(f"      {label} page {page}: {len(l1_items)} L1 items")
            l1_total += len(l1_items)

            for n1 in l1_items:
                n1["_kg_level"] = base_level + 1
                n1["_kg_parent_code"] = parent_code_for_l1
                n1["_kg_parent_title"] = root_title
                all_narrower.append(n1)
                l2_items = n1.get("domainNarrower", [])
                l2_total += len(l2_items)
                for n2 in l2_items:
                    n2["_kg_level"] = base_level + 2
                    n2["_kg_parent_code"] = n1.get("code", "")
                    n2["_kg_parent_title"] = n1.get("title", "")
                    all_narrower.append(n2)
                    l3_items = n2.get("domainNarrower", [])
                    l3_total += len(l3_items)
                    for n3 in l3_items:
                        n3["_kg_level"] = base_level + 3
                        n3["_kg_parent_code"] = n2.get("code", "")
                        n3["_kg_parent_title"] = n2.get("title", "")
                        all_narrower.append(n3)
                        l3_codes.append(n3.get("code", ""))
                        l3_titles[n3.get("code", "")] = n3.get("title", "")

            if len(l1_items) < SIZE:
                break
            offset += SIZE
            page += 1

        return all_narrower, l3_codes, l3_titles, l1_total, l2_total, l3_total, api_failed

    def get_domain_narrower(self, lexical_code: str, domain: str = "Problem", root_title: str = "") -> List[Dict]:
        """Fetch up to 6 levels: Query 1 (L1-L3) + Query 2 (L4-L6 per L3 code)."""
        gql_domain = domain.lower()
        fragment_map = {"problem": "ProblemLexical", "procedure": "ProcedureLexical", "medication": "MedicationLexical"}
        fragment = fragment_map.get(gql_domain, "ProblemLexical")

        # Query 1: L1, L2, L3 with pagination
        all_narrower, l3_codes, l3_titles, l1_count, l2_count, l3_count, q1_failed = self._fetch_3_levels(
            lexical_code, domain, fragment, label="Q1",
            base_level=0, root_code=lexical_code, root_title=root_title,
        )
        print(f"    Q1: L1={l1_count}, L2={l2_count}, L3={l3_count}, subtotal={len(all_narrower)}")

        if q1_failed:
            print(f"    Q1 API failure — result not cached")
            return None  # signal to caller: do not cache this result

        # Query 2: For each unique L3 code, fetch L4, L5, L6
        l4_count = 0
        l5_count = 0
        l6_count = 0
        seen_l3 = set()
        unique_l3 = [c for c in l3_codes if c and c not in seen_l3 and not seen_l3.add(c)]

        if unique_l3:
            print(f"    Q2: expanding {len(unique_l3)} unique L3 codes...")

        for l3_code in unique_l3:
            deeper, _, _, l4, l5, l6, _ = self._fetch_3_levels(
                l3_code, domain, fragment,
                base_level=3, root_code=l3_code, root_title=l3_titles.get(l3_code, ""),
            )
            if deeper:
                all_narrower.extend(deeper)
                l4_count += l4
                l5_count += l5
                l6_count += l6

        if unique_l3:
            print(f"    Q2: L4={l4_count}, L5={l5_count}, L6={l6_count}")

        print(f"    TOTAL: L1={l1_count}, L2={l2_count}, L3={l3_count}, L4={l4_count}, L5={l5_count}, L6={l6_count}, all={len(all_narrower)}")
        return all_narrower

    def _build_refinement_query(self, offset: int = 0, size: int = 250) -> str:
        """Build flat refinementNarrower query for Problem domain."""
        return f"""query GetRefinementNarrower($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    ... on ProblemLexical {{
      refinementNarrower(depth: 10, offset: {offset}, size: {size}) {{
        code
        title
        ... on ProblemLexical {{
          mappings {{ code title codeSystem relationshipType }}
          appliedRefinements(offset: 0, size: 20) {{ code title }}
          numberOfRefinementChildren
        }}
      }}
    }}
  }}
}}"""

    def get_refinement_narrower(self, lexical_code: str, root_title: str = "") -> Optional[List[Dict]]:
        """Fetch Problem domain children via refinementNarrower (flat, depth=10).
        Returns None on first-page API failure (do not cache)."""
        SIZE = 250
        all_narrower = []
        offset = 0
        page = 1
        api_failed = False

        while True:
            query = self._build_refinement_query(offset, SIZE)
            result = self._graphql(query, {"code": lexical_code, "domain": "problem"})
            if not result.get("success") or not result.get("data"):
                if page == 1:
                    api_failed = True
                break
            lexical = result["data"].get("lexical")
            if not lexical:
                break

            items = lexical.get("refinementNarrower", [])
            if page > 1:
                print(f"      refinement page {page}: {len(items)} items")

            for item in items:
                applied = item.get("appliedRefinements", [])
                item["_kg_level"] = len(applied) + 1
                if applied:
                    item["_kg_parent_code"] = applied[-1].get("code", lexical_code)
                    item["_kg_parent_title"] = applied[-1].get("title", root_title)
                else:
                    item["_kg_parent_code"] = lexical_code
                    item["_kg_parent_title"] = root_title
                all_narrower.append(item)

            if len(items) < SIZE:
                break
            offset += SIZE
            page += 1

        if api_failed:
            print(f"    refinementNarrower API failure — result not cached")
            return None

        level_counts = {}
        for item in all_narrower:
            lvl = item.get("_kg_level", 0)
            level_counts[lvl] = level_counts.get(lvl, 0) + 1
        level_str = ", ".join(f"L{k}={v}" for k, v in sorted(level_counts.items()))
        print(f"    REFINEMENT TOTAL: {level_str}, all={len(all_narrower)}")
        return all_narrower

    def _build_synonyms_query(self, fragment: str) -> str:
        return f"""query GetSynonyms($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    ... on {fragment} {{
      synonyms {{
        code
        title
        ... on {fragment} {{
          mappings {{ code title codeSystem relationshipType }}
        }}
      }}
    }}
  }}
}}"""

    def get_kg_synonyms(self, lexical_code: str, domain: str) -> List["NormalizedCode"]:
        """Fetch KG synonyms for a lexical code and return as NormalizedCode objects."""
        gql_domain = domain.lower()
        fragment_map = {"problem": "ProblemLexical", "procedure": "ProcedureLexical", "medication": "MedicationLexical"}
        fragment = fragment_map.get(gql_domain, "ProblemLexical")

        result = self._graphql(self._build_synonyms_query(fragment), {"code": lexical_code, "domain": gql_domain})
        if not result.get("success"):
            return []
        lexical = result.get("data", {}).get("lexical")
        if not lexical:
            return []

        synonym_codes = []
        for syn in (lexical.get("synonyms") or []):
            syn_lexical = str(syn.get("code", ""))
            syn_title = syn.get("title", "")
            if not syn_lexical:
                continue

            codes = self._extract_kg_mappings({"mappings": syn.get("mappings") or []})

            nc = NormalizedCode(
                input_term=syn_title,
                source_column="KG Synonym",
                domain=domain,
                imo_code=syn_lexical,
                imo_title=syn_title,
                lexical_code=syn_lexical,
                concept_code=syn_lexical,
                score=1.0,
            )

            if gql_domain == "medication":
                rxnorm = codes.get("rxnorm", [])
                if rxnorm:
                    nc.rxnorm_code = rxnorm[0]["code"]
                    nc.rxnorm_title = rxnorm[0]["title"]
            else:
                icd10 = codes.get("icd10cm", [])
                if icd10:
                    nc.icd10cm_code = icd10[0]["code"]
                    nc.icd10cm_title = icd10[0]["title"]
                snomed = codes.get("snomedInternational", [])
                if snomed:
                    nc.snomed_code = snomed[0]["code"]
                    nc.snomed_title = snomed[0]["title"]

            synonym_codes.append(nc)
        return synonym_codes

    def _build_containing_meds_query(self, offset: int = 0, size: int = 250) -> str:
        """Build query to fetch domainNarrower branches + containingMedications with mappings."""
        return f"""query GetContainingMeds($code: String!, $domain: IMODomain!) {{
  lexical(code: $code, domain: $domain) {{
    code
    title
    ... on MedicationLexical {{
      domainNarrower(offset: {offset}, size: {size}) {{
        code
        title
      }}
      containingMedications {{
        code
        title
        ... on MedicationLexical {{
          mappings {{ code title codeSystem }}
        }}
      }}
    }}
  }}
}}"""

    def _fetch_containing_meds(self, lexical_code: str) -> Dict:
        """Fetch domainNarrower (paginated) + containingMedications with RxNorm mappings."""
        SIZE = 250
        all_narrower = []
        containing_meds = []
        offset = 0
        first_page = True

        while True:
            query = self._build_containing_meds_query(offset, SIZE)
            result = self._graphql(query, {"code": lexical_code, "domain": "medication"})
            if not result.get("success"):
                break
            lexical = result.get("data", {}).get("lexical")
            if not lexical:
                break

            l1_items = lexical.get("domainNarrower", [])
            all_narrower.extend(l1_items)

            if first_page:
                containing_meds = lexical.get("containingMedications", []) or []
                first_page = False

            if len(l1_items) < SIZE:
                break
            offset += SIZE

        return {"domainNarrower": all_narrower, "containingMedications": containing_meds}

    def expand_medication_via_containing(self, nc: NormalizedCode) -> List[ExpandedCode]:
        """Expand medication using containingMedications flow (med-id approach).
        Single substance: containingMedications directly.
        Compound drug (non-empty domainNarrower): recurse into each branch first."""
        if not nc.lexical_code:
            return []

        print(f"    containingMedications flow: '{nc.imo_title}' ({nc.lexical_code})")

        # Step 1: Get initial containingMedications + domainNarrower branches
        result = self._fetch_containing_meds(nc.lexical_code)
        domain_narrower = result["domainNarrower"]
        all_containing = list(result["containingMedications"])
        seen_codes = {m.get("code") for m in all_containing if m.get("code")}

        print(f"      branches={len(domain_narrower)}, containingMedications={len(all_containing)}")

        # Step 2: Compound drug — recurse into each domainNarrower branch
        if domain_narrower:
            print(f"      Compound: recursing into {len(domain_narrower)} branch(es)")
            for branch in domain_narrower:
                branch_code = branch.get("code", "")
                if not branch_code:
                    continue
                branch_result = self._fetch_containing_meds(branch_code)
                for m in branch_result["containingMedications"]:
                    if m.get("code") and m["code"] not in seen_codes:
                        seen_codes.add(m["code"])
                        all_containing.append(m)
            print(f"      Total after recursion: {len(all_containing)}")

        # Step 3+4: For each containingMedication, extract RxNorm leaf codes.
        # Fast path: if the containingMedication already has RxNorm mappings from the initial
        # query it is itself the leaf SCD/SBD product — skip the extra _fetch_3_levels call.
        # Slow path (no direct RxNorm): traverse L1-L3 to find leaf nodes, as before.
        expanded = []
        seen_rxnorm: set = set()
        api_calls_skipped = 0

        for i, containing in enumerate(all_containing):
            containing_code = containing.get("code", "")
            if not containing_code:
                continue

            # Progress via logger (stderr) so it bypasses the per-thread stdout buffer
            # and appears immediately in CloudWatch even while the video is still in progress
            if (i + 1) % 10 == 0 or i == 0:
                logger.info("[containingMeds %d/%d] %s", i + 1, len(all_containing), containing_code)

            direct_rxnorm = [
                m for m in (containing.get("mappings") or [])
                if m.get("codeSystem") == "rxnorm" and m.get("code")
            ]

            if direct_rxnorm:
                # Already have RxNorm from the initial containingMedications query — no extra API call
                leaf_items = [{"code": containing_code,
                               "title": containing.get("title", ""),
                               "mappings": containing.get("mappings") or []}]
                api_calls_skipped += 1
            else:
                # No direct RxNorm — traverse L1-L3 to find leaf SCD/SBD nodes
                all_items, _, _, _, _, _, _ = self._fetch_3_levels(
                    containing_code, "Medication", "MedicationLexical"
                )
                if not all_items:
                    leaf_items = [{"code": containing_code,
                                   "title": containing.get("title", ""),
                                   "mappings": containing.get("mappings") or []}]
                else:
                    # L1/L2: have domainNarrower → parents; L3: no domainNarrower → leaf
                    parent_codes = {
                        item["code"] for item in all_items
                        if item.get("domainNarrower") and item.get("code")
                    }
                    leaf_items = [item for item in all_items if item.get("code", "") not in parent_codes]

            for leaf in leaf_items:
                rxnorm_codes = [
                    {"code": m["code"], "title": m.get("title", ""), "relationshipType": ""}
                    for m in (leaf.get("mappings") or [])
                    if m.get("codeSystem") == "rxnorm"
                    and m.get("code")
                    and m["code"] not in seen_rxnorm
                ]
                for r in rxnorm_codes:
                    seen_rxnorm.add(r["code"])
                if not rxnorm_codes:
                    continue
                expanded.append(ExpandedCode(
                    parent_input_term=nc.input_term,
                    parent_imo_code=nc.imo_code,
                    parent_title=nc.imo_title,
                    parent_lexical_code=nc.lexical_code,
                    domain=nc.domain,
                    relationship="containingMedications",
                    narrower_lexical_code=leaf.get("code", ""),
                    narrower_title=leaf.get("title", ""),
                    kg_level=leaf.get("_kg_level", 0),
                    kg_parent_code=leaf.get("_kg_parent_code", ""),
                    kg_parent_title=leaf.get("_kg_parent_title", ""),
                    rxnorm_codes=rxnorm_codes,
                ))

        print(f"      -> {len(expanded)} leaf SCD/SBD products with RxNorm codes "
              f"({api_calls_skipped}/{len(all_containing)} used direct mappings, skipped _fetch_3_levels)")
        return expanded

    def expand_code(self, nc: NormalizedCode) -> Optional[List[ExpandedCode]]:
        """Expand a single NormalizedCode via KG hierarchy.
        Problem domain uses refinementNarrower; Procedure uses domainNarrower.
        Returns None if the KG API failed (caller should not cache this result)."""
        if not nc.lexical_code:
            return []

        if nc.domain == "Problem":
            narrower = self.get_refinement_narrower(nc.lexical_code, root_title=nc.imo_title)
            rel = "refinementNarrower"
        else:
            narrower = self.get_domain_narrower(nc.lexical_code, nc.domain, root_title=nc.imo_title)
            rel = "domainNarrower"
        if narrower is None:
            return None  # KG API failure — propagate to skip caching
        expanded = []
        for n in narrower:
            codes = self._extract_kg_mappings(n)
            expanded.append(ExpandedCode(
                parent_input_term=nc.input_term,
                parent_imo_code=nc.imo_code,
                parent_title=nc.imo_title,
                parent_lexical_code=nc.lexical_code,
                domain=nc.domain,
                relationship=rel,
                narrower_lexical_code=n.get("code", ""),
                narrower_title=n.get("title", ""),
                kg_level=n.get("_kg_level", 0),
                kg_parent_code=n.get("_kg_parent_code", ""),
                kg_parent_title=n.get("_kg_parent_title", ""),
                icd10cm_codes=codes["icd10cm"],
                snomed_codes=codes["snomedInternational"],
                icd9cm_codes=codes["icd9cm"],
                cpt_codes=codes["cpt"],
                icd10pcs_codes=codes["icd10pcs"],
                hcpcs_codes=codes["hcpcs"],
                loinc_codes=codes["loinc"],
                rxnorm_codes=codes["rxnorm"],
            ))
        return expanded

    def _extract_kg_mappings(self, narrower_item: Dict) -> Dict[str, List[Dict]]:
        """Extract code system mappings from a KG narrower concept."""
        codes = {"icd10cm": [], "snomedInternational": [], "icd9cm": [],
                 "cpt": [], "icd10pcs": [], "hcpcs": [], "loinc": [], "rxnorm": []}
        for m in narrower_item.get("mappings", []):
            cs = m.get("codeSystem", "")
            if cs in codes:
                entry = {
                    "code": m.get("code", ""),
                    "title": m.get("title", ""),
                    "relationshipType": m.get("relationshipType", ""),
                }
                if entry["code"]:
                    codes[cs].append(entry)
        return codes
