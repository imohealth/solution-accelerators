"""
Phenotype → Value Set Pipeline.

Reads a phenotype spreadsheet, normalizes concepts to IMO lexical codes via the
Precision Normalize API, expands them through the IMO Knowledge Graph
(refinementNarrower for Problem; domainNarrower for Procedure;
containingMedications for Medication), and publishes the resulting value sets
to the IMO Precision Set Editor.

Expected spreadsheet columns (first row is the header, case-insensitive):

    phenotype_title
    primary_domain
    primary_concepts
    secondary_domain
    secondary_concepts
    exclusion_concepts_domain
    exclusion_concepts

Multi-value cells use `;`, newline, or `|` as separators.
"""

import argparse
import json
import logging
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import openpyxl

import config
from api_client import ApiClient, NormalizedCode, ExpandedCode
import precision_sets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_WORKERS = 8  # parallel threads for normalize + KG expand


# ── Data classes ───────────────────────────────────────────────────────

INCLUSION = "inclusion"
EXCLUSION = "exclusion"


@dataclass
class Phenotype:
    row_number: int
    title: str
    primary_domain: str
    primary_concepts: List[str]
    secondary_domain: str
    secondary_concepts: List[str]
    exclusion_concepts_domain: str
    exclusion_concepts: List[str]

    def inclusion_concepts_by_domain(self) -> Dict[str, List[str]]:
        """Group primary + secondary inclusion concepts by their domain.

        Precision Set Editor does not allow a single value set to span
        multiple domains, so concepts from different domains become
        separate value sets.
        """
        buckets: Dict[str, List[str]] = {}
        if self.primary_domain and self.primary_concepts:
            buckets.setdefault(self.primary_domain, []).extend(self.primary_concepts)
        if self.secondary_domain and self.secondary_concepts:
            buckets.setdefault(self.secondary_domain, []).extend(self.secondary_concepts)
        return {d: list(dict.fromkeys(c)) for d, c in buckets.items()}

    def exclusion_target_domains(self, inclusion_domains: List[str]) -> List[str]:
        """Return the domains that should receive an exclusion value set.

        * Specific domain → that domain only.
        * Blank or `All` → every inclusion domain the phenotype has.
        """
        if not self.exclusion_concepts:
            return []
        if self.exclusion_concepts_domain in ("", "All"):
            return list(inclusion_domains)
        return [self.exclusion_concepts_domain]


@dataclass
class ValueSetJob:
    """One generated value set: inclusion or exclusion for a phenotype domain."""
    phenotype: Phenotype
    domain: str
    kind: str  # INCLUSION or EXCLUSION
    concepts: List[str]

    @property
    def title(self) -> str:
        return f"{self.phenotype.title}_{self.domain}_{self.kind}"


@dataclass
class ValueSetResult:
    job: ValueSetJob
    normalized_codes: List[NormalizedCode] = field(default_factory=list)
    synonym_titles: List[str] = field(default_factory=list)
    kg_expansions: List[ExpandedCode] = field(default_factory=list)


# ── Spreadsheet loading ────────────────────────────────────────────────

REQUIRED_COLUMNS = (
    "phenotype_title",
    "primary_domain",
    "primary_concepts",
    "secondary_domain",
    "secondary_concepts",
    "exclusion_concepts_domain",
    "exclusion_concepts",
)

_SEPARATORS = re.compile(r"[;\n|]+")


def _cell(value) -> str:
    return "" if value is None else str(value).strip()


def _split_concepts(value) -> List[str]:
    text = _cell(value)
    if not text:
        return []
    return list(dict.fromkeys(piece.strip() for piece in _SEPARATORS.split(text) if piece.strip()))


def _map_domain(raw: str, *, row_number: int, field_name: str, allow_blank: bool = False) -> str:
    """Map a free-text domain label from the spreadsheet to a pipeline domain name."""
    label = raw.strip().lower()
    if not label:
        if allow_blank:
            return ""
        raise ValueError(f"Row {row_number}: {field_name} is required")
    # Pass through sentinel values as-is for exclusion_concepts_domain
    if field_name == "exclusion_concepts_domain" and label in {"all", "all domains"}:
        return "All"
    mapped = config.DOMAIN_MAP.get(label)
    if not mapped:
        raise ValueError(f"Row {row_number}: unsupported {field_name} value {raw!r}")
    if mapped not in config.SUPPORTED_DOMAINS:
        raise ValueError(
            f"Row {row_number}: {field_name}={raw!r} maps to unsupported domain {mapped!r}"
        )
    return mapped


def load_spreadsheet(path: str, sheet_name: Optional[str] = None) -> List[Phenotype]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet_name:
            if sheet_name not in wb.sheetnames:
                raise ValueError(
                    f"Worksheet {sheet_name!r} not found; available: {', '.join(wb.sheetnames)}"
                )
            ws = wb[sheet_name]
        else:
            ws = wb.active

        header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())
        headers = [_cell(v).lower() for v in header]
        col = {name: idx for idx, name in enumerate(headers) if name}
        missing = [c for c in REQUIRED_COLUMNS if c not in col]
        if missing:
            raise ValueError(f"Missing required spreadsheet columns: {', '.join(missing)}")

        phenotypes: List[Phenotype] = []
        for row_num, values in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            def _val(key: str) -> str:
                idx = col[key]
                return _cell(values[idx] if idx < len(values) else None)

            if not any(_val(c) for c in REQUIRED_COLUMNS):
                continue
            title = _val("phenotype_title")
            if not title:
                raise ValueError(f"Row {row_num}: phenotype_title is required")

            primary_concepts = _split_concepts(_val("primary_concepts"))
            secondary_concepts = _split_concepts(_val("secondary_concepts"))
            exclusion_concepts = _split_concepts(_val("exclusion_concepts"))

            primary_domain = _map_domain(_val("primary_domain"), row_number=row_num,
                                         field_name="primary_domain")
            secondary_domain = _map_domain(_val("secondary_domain"), row_number=row_num,
                                           field_name="secondary_domain", allow_blank=True)
            if secondary_concepts and not secondary_domain:
                raise ValueError(
                    f"Row {row_num}: secondary_concepts given without secondary_domain"
                )
            exclusion_domain = _map_domain(
                _val("exclusion_concepts_domain"), row_number=row_num,
                field_name="exclusion_concepts_domain", allow_blank=True,
            )

            phenotypes.append(Phenotype(
                row_number=row_num,
                title=title,
                primary_domain=primary_domain,
                primary_concepts=primary_concepts,
                secondary_domain=secondary_domain,
                secondary_concepts=secondary_concepts,
                exclusion_concepts_domain=exclusion_domain,
                exclusion_concepts=exclusion_concepts,
            ))
        print(f"Loaded {len(phenotypes)} phenotype(s) from spreadsheet")
        return phenotypes
    finally:
        wb.close()


def fan_out_value_sets(phenotypes: List[Phenotype]) -> List[ValueSetJob]:
    """Fan out each phenotype into inclusion + exclusion value sets per domain.

    Each phenotype produces:
      * one inclusion VS per domain that has inclusion concepts,
        titled '<phenotype_title>_<domain>_inclusion'
      * one exclusion VS per targeted domain,
        titled '<phenotype_title>_<domain>_exclusion'

    Precision Set Editor does not allow mixed-domain value sets, so concepts
    from different domains are always split into their own VSes.
    """
    jobs: List[ValueSetJob] = []
    seen_titles: Set[str] = set()

    def _add(job: ValueSetJob) -> None:
        if job.title in seen_titles:
            raise ValueError(
                f"Duplicate value set title {job.title!r}; phenotype titles must be unique"
            )
        seen_titles.add(job.title)
        jobs.append(job)

    for p in phenotypes:
        inclusion_buckets = p.inclusion_concepts_by_domain()
        if not inclusion_buckets and not p.exclusion_concepts:
            print(f"  Row {p.row_number}: skipping {p.title!r} — no concepts")
            continue

        for domain, concepts in inclusion_buckets.items():
            _add(ValueSetJob(phenotype=p, domain=domain, kind=INCLUSION, concepts=concepts))

        exclusion_domains = p.exclusion_target_domains(list(inclusion_buckets.keys()))
        for domain in exclusion_domains:
            _add(ValueSetJob(
                phenotype=p, domain=domain, kind=EXCLUSION,
                concepts=list(dict.fromkeys(p.exclusion_concepts)),
            ))

    print(f"Fanned out to {len(jobs)} value set job(s) across domains")
    return jobs


# ── Normalize + KG Expand pipeline ─────────────────────────────────────

class PhenotypePipeline:

    def __init__(self):
        self.api_client = ApiClient()
        self._norm_cache: Dict[Tuple[str, str], Optional[NormalizedCode]] = {}
        self._expand_cache: Dict[Tuple[str, str], List[ExpandedCode]] = {}
        self._cache_lock = threading.Lock()

    # ── Normalize ─────────────────────────────────────────────────────

    def _normalize_cached(self, concept: str, domain: str, label: str) -> Optional[NormalizedCode]:
        key = (concept.lower().strip(), domain)
        with self._cache_lock:
            if key in self._norm_cache:
                return self._norm_cache[key]
        result = self.api_client.normalize_and_extract(concept, domain, label)
        with self._cache_lock:
            self._norm_cache[key] = result
        return result

    def _expand_cached(self, nc: NormalizedCode) -> List[ExpandedCode]:
        key = (nc.lexical_code, nc.domain)
        with self._cache_lock:
            if key in self._expand_cache:
                return self._expand_cache[key]
        if nc.domain == "Medication":
            result = self.api_client.expand_medication_via_containing(nc)
        else:
            result = self.api_client.expand_code(nc)
        if result is None:
            return []
        with self._cache_lock:
            self._expand_cache[key] = result
        return result

    def normalize_job(self, job: ValueSetJob) -> ValueSetResult:
        codes: List[NormalizedCode] = []
        seen: Set[str] = set()
        synonyms: List[str] = []

        for concept in job.concepts:
            nc = self._normalize_cached(concept, job.domain, job.kind)
            if not nc or not nc.imo_code or nc.imo_code in seen:
                continue
            if nc.score < config.NORMALIZE_SCORE_THRESHOLD:
                print(f"  SKIP (score={nc.score:.3f} < {config.NORMALIZE_SCORE_THRESHOLD}): "
                      f"'{nc.input_term}' -> '{nc.imo_title}'")
                continue
            seen.add(nc.imo_code)
            codes.append(nc)
            print(f"  Normalize: '{concept}' -> '{nc.imo_title}' "
                  f"(lexical={nc.lexical_code}, score={nc.score:.3f})")
            for syn in self.api_client.get_kg_synonyms(nc.lexical_code, nc.domain):
                if syn.imo_title and syn.imo_title not in synonyms:
                    synonyms.append(syn.imo_title)

        return ValueSetResult(job=job, normalized_codes=codes, synonym_titles=synonyms)

    # ── KG expand ─────────────────────────────────────────────────────

    def expand_job(self, result: ValueSetResult) -> ValueSetResult:
        expanded_lexicals: Set[str] = set()
        expanded_codes: List[ExpandedCode] = []

        for nc in result.normalized_codes:
            if nc.lexical_code in expanded_lexicals:
                continue
            expanded_lexicals.add(nc.lexical_code)
            children = self._expand_cached(nc)
            expanded_codes.extend(children)
            label = f"'{nc.input_term}' -> '{nc.imo_title}' ({nc.lexical_code})"
            print(f"  {label} -> {len(children)} children")

        result.kg_expansions = expanded_codes
        return result

    # ── Parallel runner ───────────────────────────────────────────────

    def normalize_all(self, jobs: List[ValueSetJob]) -> List[ValueSetResult]:
        total = len(jobs)

        def _run(idx_job):
            idx, job = idx_job
            print(f"\n[Normalize {idx + 1}/{total}] {job.title}")
            r = self.normalize_job(job)
            print(f"  -> {len(r.normalized_codes)} unique codes")
            return r

        with ThreadPoolExecutor(max_workers=_WORKERS) as executor:
            return list(executor.map(_run, enumerate(jobs)))

    def expand_all(self, results: List[ValueSetResult]) -> List[ValueSetResult]:
        total = len(results)

        def _run(idx_res):
            idx, r = idx_res
            print(f"\n[Expand {idx + 1}/{total}] {r.job.title} "
                  f"({len(r.normalized_codes)} codes)")
            return self.expand_job(r)

        with ThreadPoolExecutor(max_workers=_WORKERS) as executor:
            return list(executor.map(_run, enumerate(results)))

    # ── JSON generation ───────────────────────────────────────────────

    def _json_filename(self, title: str) -> str:
        return re.sub(r"[^\w\s\-]", "", title).strip().replace(" ", "_")[:80] + ".json"

    def build_valueset_json(self, result: ValueSetResult) -> Dict:
        """Build a single-kind value set.

        Every rule is an `Include`; the kind (inclusion/exclusion) lives in
        the title, not in the rule mapType. Precision Set Editor does not
        permit mixed-domain value sets, so a single VS always carries one
        domain's code systems.
        """
        job = result.job
        is_medication = job.domain == "Medication"
        code_system = config.DOMAIN_CODE_SYSTEM.get(job.domain)  # None for Medication

        rules: List[Dict] = []
        seen_codes: Set[str] = set()

        if is_medication:
            seen_ndc: Set[str] = set()
            for nc in result.normalized_codes:
                if nc.rxnorm_code and nc.rxnorm_code not in seen_codes:
                    seen_codes.add(nc.rxnorm_code)
                    rules.append({
                        "codeSystem": "RX_NORM", "code": nc.rxnorm_code, "mapType": "Include",
                        "description": nc.rxnorm_title or nc.imo_title,
                        "level": 0, "parentNodeCode": "", "parentNodeTitle": "",
                    })
                for ndc in nc.ndc_codes:
                    code = ndc.get("code", "")
                    if code and code not in seen_ndc:
                        seen_ndc.add(code)
                        rules.append({
                            "codeSystem": "NDC", "code": code, "mapType": "Include",
                            "description": ndc.get("title", ""),
                            "level": 0, "parentNodeCode": "", "parentNodeTitle": "",
                        })
            for ec in result.kg_expansions:
                for rx in ec.rxnorm_codes:
                    code = rx.get("code", "")
                    if code and code not in seen_codes:
                        seen_codes.add(code)
                        rules.append({
                            "codeSystem": "RX_NORM", "code": code, "mapType": "Include",
                            "description": rx.get("title", ec.narrower_title),
                            "level": ec.kg_level,
                            "parentNodeCode": ec.kg_parent_code,
                            "parentNodeTitle": ec.kg_parent_title,
                        })

        else:
            for nc in result.normalized_codes:
                if nc.lexical_code and nc.lexical_code not in seen_codes:
                    seen_codes.add(nc.lexical_code)
                    rules.append({
                        "codeSystem": code_system, "code": nc.lexical_code, "mapType": "Include",
                        "description": nc.imo_title,
                        "level": 0, "parentNodeCode": "", "parentNodeTitle": "",
                    })
            for ec in result.kg_expansions:
                code = ec.narrower_lexical_code
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    rules.append({
                        "codeSystem": code_system, "code": code, "mapType": "Include",
                        "description": ec.narrower_title,
                        "level": ec.kg_level,
                        "parentNodeCode": ec.kg_parent_code,
                        "parentNodeTitle": ec.kg_parent_title,
                    })

        inclusion_criteria = "; ".join(job.concepts)
        if result.synonym_titles:
            inclusion_criteria = (
                f"{inclusion_criteria}; " if inclusion_criteria else ""
            ) + "; ".join(result.synonym_titles)

        return {
            "name": job.title,
            "domain": job.domain,
            "scope": (
                f"{config.PS_FHIR_SCOPE_PREFIX} - {job.title}, "
                f"version={config.VALUESET_ATTRIBUTE_VERSION}"
            ),
            "kind": job.kind,
            "inclusionCriteria": inclusion_criteria,
            "exclusionCriteria": "",
            "totalUniqueCodes": len(rules),
            "rulesToAddOrUpdate": rules,
        }

    def write_valueset_jsons(self, results: List[ValueSetResult], output_dir: str) -> List[str]:
        json_dir = os.path.join(output_dir, "valueset_jsons")
        os.makedirs(json_dir, exist_ok=True)
        paths: List[str] = []
        for r in results:
            payload = self.build_valueset_json(r)
            filename = self._json_filename(r.job.title)
            filepath = os.path.join(json_dir, filename)
            with open(filepath, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            paths.append(filepath)
            print(f"  {r.job.title} -> {payload['totalUniqueCodes']} unique codes -> {filename}")
        print(f"\n{len(paths)} value set JSON files saved to: {json_dir}")
        return paths

    # ── Publish ───────────────────────────────────────────────────────

    def publish(self, json_paths: List[str]) -> List[Dict]:
        return precision_sets.publish_valuesets(json_paths)

    def republish(self, json_paths: List[str]) -> List[Dict]:
        return precision_sets.republish_existing_valuesets(json_paths)

    # ── Publish-only path ─────────────────────────────────────────────

    def publish_existing_jsons(self, output_dir: str, republish: bool = False) -> List[str]:
        """Publish the JSONs already in <output_dir>/valueset_jsons/ without regenerating.

        Use after a prior dry run to push a reviewed output tree straight to
        Precision Sets. `republish=True` creates a draft + updates rules on
        already-published value sets; otherwise the default publish flow is used
        (it handles both existing titles and new VSes via the FHIR title lookup).
        """
        json_dir = os.path.join(output_dir, "valueset_jsons")
        if not os.path.isdir(json_dir):
            raise FileNotFoundError(f"No valueset_jsons/ under {output_dir}; run without --publish-only first")
        json_paths = sorted(
            os.path.join(json_dir, name)
            for name in os.listdir(json_dir)
            if name.endswith(".json")
        )
        if not json_paths:
            raise FileNotFoundError(f"No .json files found in {json_dir}")
        print(f"\n{'='*60}")
        print(f"PUBLISH-ONLY: {len(json_paths)} existing JSON file(s) from {json_dir}")
        print(f"  Mode: {'republish' if republish else 'publish'}")
        print(f"{'='*60}")
        if republish:
            self.republish(json_paths)
        else:
            self.publish(json_paths)
        return json_paths

    # ── End-to-end run ────────────────────────────────────────────────

    def run(self, input_path: str, output_dir: str, sheet_name: Optional[str] = None,
            publish: bool = False, republish: bool = False) -> List[str]:
        os.makedirs(output_dir, exist_ok=True)
        phenotypes = load_spreadsheet(input_path, sheet_name)
        jobs = fan_out_value_sets(phenotypes)
        if not jobs:
            print("No value set jobs to run.")
            return []

        normalized = self.normalize_all(jobs)
        expanded = self.expand_all(normalized)
        json_paths = self.write_valueset_jsons(expanded, output_dir)

        total_norm = sum(len(r.normalized_codes) for r in expanded)
        total_kg = sum(len(r.kg_expansions) for r in expanded)
        print(f"\n{'='*60}")
        print(f"PIPELINE COMPLETE")
        print(f"  Phenotypes        : {len(phenotypes)}")
        print(f"  Value sets        : {len(json_paths)}")
        print(f"  Normalize codes   : {total_norm}")
        print(f"  KG expanded codes : {total_kg}")
        print(f"  Total codes       : {total_norm + total_kg}")
        print(f"{'='*60}")

        if republish:
            self.republish(json_paths)
        elif publish:
            self.publish(json_paths)
        return json_paths


# ── CLI ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",
                        help="Path to the phenotype .xlsx spreadsheet "
                             "(required unless --publish-only is set)")
    parser.add_argument("--output",
                        default=config.OUTPUT_DIR,
                        help="Output directory for generated JSON (default from config)")
    parser.add_argument("--sheet", default=None,
                        help="Worksheet name (defaults to the active worksheet)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--publish", action="store_true",
                       help="Publish new value sets to IMO Precision Sets")
    group.add_argument("--republish", action="store_true",
                       help="Create new draft + update rules for already-published value sets")
    parser.add_argument("--publish-only", action="store_true",
                        help="Skip normalize/KG/JSON generation and publish the existing "
                             "JSONs under <output>/valueset_jsons/ "
                             "(uses --republish semantics if also set)")
    args = parser.parse_args()

    if not args.publish_only and not args.input:
        parser.error("--input is required unless --publish-only is set")

    os.makedirs(args.output, exist_ok=True)
    log_path = os.path.join(args.output, f"phenotype_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    log_file = open(log_path, "w", encoding="utf-8", buffering=1)

    class _Tee:
        def __init__(self, stream):
            self._stream = stream
        def write(self, data):
            log_file.write(data)
            self._stream.write(data)
        def flush(self):
            log_file.flush()
            self._stream.flush()
        def __getattr__(self, name):
            return getattr(self._stream, name)

    sys.stdout = _Tee(sys.stdout)
    sys.stderr = _Tee(sys.stderr)
    print(f"Logging to: {log_path}\n")

    try:
        pipeline = PhenotypePipeline()
        if args.publish_only:
            pipeline.publish_existing_jsons(args.output, republish=args.republish)
        else:
            pipeline.run(
                input_path=args.input,
                output_dir=args.output,
                sheet_name=args.sheet,
                publish=args.publish,
                republish=args.republish,
            )
    finally:
        sys.stdout = sys.stdout._stream  # type: ignore[attr-defined]
        sys.stderr = sys.stderr._stream  # type: ignore[attr-defined]
        log_file.close()


if __name__ == "__main__":
    main()
