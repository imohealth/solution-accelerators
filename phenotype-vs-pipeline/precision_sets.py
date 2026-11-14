"""
Precision Sets API client — create, push rules, expand, and publish value sets.
"""

import json
import os
import sys
import time
import logging
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import config

logger = logging.getLogger(__name__)

_token: Optional[str] = None
_token_expiry: float = 0
_token_lock = threading.Lock()
_print_lock  = threading.Lock()

MAX_PUBLISH_WORKERS = 4


def get_token() -> str:
    global _token, _token_expiry
    if _token and time.time() < _token_expiry:
        return _token
    with _token_lock:
        if _token and time.time() < _token_expiry:
            return _token
        resp = requests.post(config.PS_AUTH_URL, json={
            "client_id": config.PS_CLIENT_ID,
            "client_secret": config.PS_CLIENT_SECRET,
            "audience": config.PS_AUDIENCE,
            "grant_type": "client_credentials",
        }, headers={"Content-Type": "application/json"}, timeout=30)
        resp.raise_for_status()
        _token = resp.json()["access_token"]
        _token_expiry = time.time() + 3540
        logger.info("Precision Sets token obtained")
        return _token


def graphql(query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
    token = get_token()
    resp = requests.post(config.PS_GRAPHQL_URL, json={
        "query": query,
        "variables": variables or {},
    }, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
    }, timeout=120)
    if not resp.ok:
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:1000]
        raise requests.HTTPError(
            f"HTTP {resp.status_code} from {config.PS_GRAPHQL_URL}\n"
            f"Body: {json.dumps(body, indent=2) if isinstance(body, dict) else body}",
            response=resp,
        )
    result = resp.json()
    if "errors" in result:
        logger.warning("GraphQL errors: %s", result["errors"])
    return result


# ── GraphQL Queries & Mutations ───────────────────────────────────────

CREATE_MUTATION = """mutation CreateNewValueSet($input: CreateNewValueSetInput!) {
  createNewValueSet(input: $input) {
    valueSet {
      valueSetId
      domain
      valueSetVersion {
        valueSetVersionId
        name
        version
        versionStatus
        expansionJobStatus
      }
    }
  }
}"""

DRAFT_MUTATION = """mutation CreateValueSetDraft($valueSetId: Int!, $versionId: Int!) {
  createValueSetDraft(valueSetId: $valueSetId, versionId: $versionId) {
    valueSet {
      valueSetId
      valueSetVersion {
        valueSetVersionId
        version
        versionStatus
      }
    }
  }
}"""

QUERY_VS = """query QueryValueSet($valueSetId: Int!) {
  valueSet(valueSetId: $valueSetId) {
    valueSetId
    valueSetVersion {
      valueSetVersionId
      version
      versionStatus
      expansionJobStatus
    }
  }
}"""

RULES_MUTATION = """mutation UpdateValueSetVersionRules($input: UpdateValueSetVersionRulesInput!) {
  updateValueSetVersionRules(input: $input) {
    valueSet {
      valueSetId
      valueSetVersion {
        valueSetVersionId
        expansionJobStatus
      }
    }
  }
}"""

SEARCH_VS = """query SearchValueSet($name: String!) {
  valueSetSearch(name: $name) {
    valueSets {
      valueSetId
      name
      valueSetVersion {
        valueSetVersionId
        version
        versionStatus
      }
    }
  }
}"""

EXPANSION_MUTATION = """mutation UpdateExpansionSetting($input: UpdateExpansionSettingInput!) {
  updateExpansionSetting(input: $input) {
    valueSet {
      valueSetId
      valueSetVersion {
        valueSetVersionId
        expansionJobStatus
        expansionMethod
      }
    }
  }
}"""

OUTPUT_QUERY = """query ValueSetOutput($valueSetId: Int!, $versionId: Int!, $page: Int, $pageSize: Int) {
  valueSetOutput(valueSetId: $valueSetId, versionId: $versionId, page: $page, pageSize: $pageSize) {
    outputCodes {
      codeSystem
      code
      description
      outputReasons
    }
    page
    pageSize
    totalCount
  }
}"""

ATTRIBUTES_MUTATION = """mutation UpdateValueSetAttributes($input: UpdateValueSetVersionAttributesInput!) {
  updateValueSetVersionAttributes(input: $input) {
    valueSetAttributes { attributeKey attributeValue }
  }
}"""

METADATA_MUTATION = """mutation UpdateValueSetVersionMetadata($input: UpdateValueSetVersionMetadataInput!) {
  updateValueSetVersionMetadata(input: $input) {
    valueSet {
      valueSetId
      valueSetVersion {
        valueSetVersionId
        name
      }
    }
  }
}"""

QUERY_VS_RULES = """query GetValueSetRules($valueSetId: Int!, $page: Int, $pageSize: Int) {
  valueSet(valueSetId: $valueSetId) {
    valueSetVersion {
      valueSetVersionId
      mappedRules(page: $page, pageSize: $pageSize) {
        rules {
          codeSystem
          code
          mapType
        }
        totalCount
      }
    }
  }
}"""

PUBLISH_MUTATION = """mutation PublishValueSet($valueSetId: Int!) {
  publishValueSet(valueSetId: $valueSetId) {
    valueSet {
      valueSetId
      valueSetVersion {
        valueSetVersionId
        version
        versionStatus
      }
    }
  }
}"""


# ── Helper functions ──────────────────────────────────────────────────

def search_existing(name: str) -> Optional[Dict]:
    try:
        resp = graphql(SEARCH_VS, {"name": name})
        matches = resp.get("data", {}).get("valueSetSearch", {}).get("valueSets", [])
        return next((m for m in matches if m["name"] == name), None)
    except Exception as e:
        logger.warning("valueSetSearch unavailable (%s) — treating '%s' as new", e, name)
        return None


def wait_for_expansion(vs_id: int, label: str = "") -> str:
    prefix = f"[{label}] " if label else ""
    for attempt in range(1, 61):
        resp = graphql(QUERY_VS, {"valueSetId": vs_id})
        status = resp["data"]["valueSet"]["valueSetVersion"]["expansionJobStatus"]
        if status is None or status.upper() in ("COMPLETED", "NONE", "FAILED", "ERROR"):
            return status or "NONE"
        # CREATED = queued but not yet running; PROCESSING = actively running — keep polling both
        print(f"    {prefix}Waiting for expansion... ({status})")
        time.sleep(5)
    return "TIMEOUT"


def get_vs_rules(vs_id: int) -> List[Dict]:
    """Fetch all mapped rules from the current (latest) version of a value set, paginating if needed."""
    PAGE_SIZE = 2000
    all_rules = []
    page = 1
    try:
        while True:
            resp = graphql(QUERY_VS_RULES, {"valueSetId": vs_id, "page": page, "pageSize": PAGE_SIZE})
            vsv = (resp.get("data", {}).get("valueSet", {}) or {}).get("valueSetVersion", {}) or {}
            mapped = vsv.get("mappedRules", {}) or {}
            batch = mapped.get("rules", []) or []
            all_rules.extend([{"codeSystem": r["codeSystem"], "code": r["code"], "mapType": r["mapType"]} for r in batch])
            total = mapped.get("totalCount", 0)
            if len(all_rules) >= total or len(batch) < PAGE_SIZE:
                break
            page += 1
        return all_rules
    except Exception as e:
        logger.warning("Could not fetch rules for vsId=%s: %s", vs_id, e)
        return []


def _log_rules_diff(vs_id: int, new_rules: List[Dict]) -> None:
    """Fetch current published rules and log a diff against new_rules."""
    current = get_vs_rules(vs_id)
    if not current:
        print(f"  Rules diff: no existing rules to compare (or fetch failed)")
        return
    current_keys = {(r["codeSystem"], r["code"], r["mapType"]) for r in current}
    new_keys     = {(r["codeSystem"], r["code"], r["mapType"]) for r in new_rules}
    added        = new_keys - current_keys
    removed      = current_keys - new_keys
    unchanged    = current_keys & new_keys
    print(f"  Rules diff vs current published version:")
    print(f"    Unchanged : {len(unchanged)}")
    print(f"    Added     : {len(added)}")
    print(f"    Removed   : {len(removed)}")
    if not added and not removed:
        print(f"    >> Draft is IDENTICAL to current published version — no rule changes")
    else:
        if added:
            for cs, code, mt in sorted(added)[:10]:
                print(f"      + {cs} {code} ({mt})")
            if len(added) > 10:
                print(f"      ... and {len(added) - 10} more added")
        if removed:
            for cs, code, mt in sorted(removed)[:10]:
                print(f"      - {cs} {code} ({mt})")
            if len(removed) > 10:
                print(f"      ... and {len(removed) - 10} more removed")


def _delete_stale_rules(vs_id: int, vsv_id: int, new_rules: List[Dict]) -> None:
    """Delete any inherited rules in the draft that are not in new_rules."""
    inherited = get_vs_rules(vs_id)
    if not inherited:
        return
    new_keys = {(r["codeSystem"], r["code"], r["mapType"]) for r in new_rules}
    stale = [r for r in inherited if (r["codeSystem"], r["code"], r["mapType"]) not in new_keys]
    if not stale:
        return
    print(f"  Removing {len(stale)} stale inherited rule(s) from draft")
    # RuleToDeleteInput only accepts codeSystem + code (no mapType)
    stale_delete = [{"codeSystem": r["codeSystem"], "code": r["code"]} for r in stale]
    resp = graphql(RULES_MUTATION, {"input": {
        "valueSetId": vs_id,
        "valueSetVersionId": vsv_id,
        "rulesToAddOrUpdate": [],
        "rulesToDelete": stale_delete,
    }})
    if resp.get("data") is None:
        err = (resp.get("errors") or [{}])[0].get("message", "Unknown error")
        print(f"  WARNING: stale rule deletion may have failed — {err}")
    else:
        print(f"  Stale rules deleted OK")


def _set_version_attribute(vs_id: int, vsv_id: int) -> None:
    """Set the version attribute on a draft version."""
    resp = graphql(ATTRIBUTES_MUTATION, {"input": {
        "valueSetId": vs_id,
        "valueSetVersionId": vsv_id,
        "valueSetAttributes": [
            {"attributeKey": "version", "attributeValue": config.VALUESET_ATTRIBUTE_VERSION, "displayOrder": 1}
        ],
        "outputAttributes": [],
    }})
    if resp.get("errors"):
        err = resp["errors"][0].get("message", "Unknown")
        print(f"  WARNING: failed to set version attribute — {err}")
    else:
        print(f"  Version attribute set: {config.VALUESET_ATTRIBUTE_VERSION}")


def _trigger_expansion(vs_id: int, vsv_id: int, label: str = "", domain: str = "") -> str:
    """Set expansion method and return final status.
    Procedure domain uses Standard; all other domains use Broad (shown as 'Extended' in PS UI).
    Toggles via the alternate method if expansion stays NONE."""
    target_method = "Standard" if domain.lower() == "procedure" else "Broad"
    alternate_method = "Broad" if target_method == "Standard" else "Standard"
    graphql(EXPANSION_MUTATION, {"input": {
        "valueSetId": vs_id, "valueSetVersionId": vsv_id, "expansionMethod": target_method,
    }})
    status = wait_for_expansion(vs_id, label)
    if status == "NONE":
        # Expansion method didn't take — toggle to alternate then back to target to force re-trigger
        graphql(EXPANSION_MUTATION, {"input": {
            "valueSetId": vs_id, "valueSetVersionId": vsv_id, "expansionMethod": alternate_method,
        }})
        time.sleep(2)
        graphql(EXPANSION_MUTATION, {"input": {
            "valueSetId": vs_id, "valueSetVersionId": vsv_id, "expansionMethod": target_method,
        }})
        status = wait_for_expansion(vs_id, label)
    return status


def _push_rules_in_batches(vs_id: int, vsv_id: int, rules: List[Dict], batch_size: int) -> None:
    """Push rules in batches, waiting for expansion between batches and retrying on conflict."""
    for i in range(0, len(rules), batch_size):
        batch = rules[i:i + batch_size]
        batch_num = i // batch_size + 1

        if i > 0:
            wait_status = wait_for_expansion(vs_id)
            print(f"    Expansion settled: {wait_status}")
            if wait_status.upper() == "ERROR":
                print(f"    [Stopping batches — expansion is ERROR, remaining rules will not be pushed]")
                return

        for attempt in range(1, 4):
            resp = graphql(RULES_MUTATION, {"input": {
                "valueSetId": vs_id,
                "valueSetVersionId": vsv_id,
                "rulesToAddOrUpdate": batch,
                "rulesToDelete": [],
            }})
            if resp.get("data") is not None:
                status = resp["data"]["updateValueSetVersionRules"]["valueSet"]["valueSetVersion"]["expansionJobStatus"]
                print(f"  Batch {batch_num}: {len(batch)} rules, expansion={status}")
                if status and status.upper() == "ERROR":
                    print(f"    [Batch {batch_num} rules that may have caused ERROR:]")
                    for r in batch:
                        print(f"      {r['codeSystem']} {r['code']} ({r['mapType']}) — {r.get('description', '')}")
                break
            err = (resp.get("errors") or [{}])[0].get("message", "Unknown error")
            if "expansion is in progress" in err.lower() and attempt < 3:
                print(f"  Batch {batch_num}: expansion still running, waiting... (attempt {attempt})")
                wait_for_expansion(vs_id)
            else:
                print(f"  Batch {batch_num}: FAILED — {err}")
                break


# ── Main publish flow ─────────────────────────────────────────────────

def _expand_and_publish_one(r: Dict) -> Dict:
    """Worker: trigger expansion, wait, fetch output count, then publish one VS.
    Buffers stdout lines and flushes them atomically so parallel output stays readable."""
    vs_id  = r["valueSetId"]
    vsv_id = r["valueSetVersionId"]
    name   = r["name"]
    lines: List[str] = [f"\n  {name} (vsId={vs_id})"]
    try:
        status = _trigger_expansion(vs_id, vsv_id, label=name, domain=r.get("domain", ""))
        r["expansionComplete"] = status.upper() == "COMPLETED"
        lines.append(f"    Expansion: {status}")
        if r["expansionComplete"]:
            resp = graphql(OUTPUT_QUERY, {
                "valueSetId": vs_id, "versionId": vsv_id, "page": 1, "pageSize": 1,
            })
            r["outputCount"] = resp["data"]["valueSetOutput"]["totalCount"]
            lines.append(f"    Output codes: {r['outputCount']}")
            resp = graphql(PUBLISH_MUTATION, {"valueSetId": vs_id})
            if resp.get("data") is None and any(
                "already published" in (e.get("message", "")).lower()
                for e in resp.get("errors", [])
            ):
                r["published"] = True
                lines.append("    Published: (already published by concurrent worker)")
            else:
                vsv = resp["data"]["publishValueSet"]["valueSet"]["valueSetVersion"]
                r["published"] = True
                lines.append(f"    Published: version={vsv['version']}, status={vsv['versionStatus']}")
        else:
            lines.append(f"    SKIPPED publish (expansion={status})")
    except Exception as e:
        logger.warning("Expand+publish failed for %s: %s", name, e)
        lines.append(f"    ERROR: {e}")
        r.setdefault("expansionComplete", False)
    with _print_lock:
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
    return r


def fetch_all_video_summary_vs() -> Dict[str, int]:
    """
    Fetch all Video Summary VSes from PS via FHIR search (paginated).
    Returns {title: valueSetId} for all VSes whose scope starts with PS_FHIR_SCOPE_PREFIX.
    """
    token = get_token()
    vs_map: Dict[str, int] = {}
    page = 1
    page_size = 100
    while True:
        resp = requests.get(
            f"{config.PS_FHIR_URL}/ValueSet/search",
            params={"searchText": config.PS_FHIR_SCOPE_PREFIX, "pageSize": page_size, "page": page},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        entries = data.get("entry", [])
        for entry in entries:
            res = entry.get("resource", {})
            title = res.get("title")
            vs_id = res.get("id")
            if title and vs_id:
                vs_map[title] = int(vs_id)
        if len(entries) < page_size:
            break
        page += 1
    print(f"  FHIR lookup: found {len(vs_map)} existing Video Summary VSes in PS")
    return vs_map


def publish_valuesets(json_paths: List[str]) -> List[Dict]:
    """
    Publish all value set JSON files to Precision Sets.
    - VSes already in PS (found via FHIR lookup) → create new draft + update rules + publish
    - VSes not in PS                             → create brand new VS + push rules + publish
    Returns list of result dicts with vsId, vsvId, ruleCount, outputCount, published status.
    """
    print(f"\n{'='*60}")
    print("PRECISION SETS PUBLISHING")
    print(f"{'='*60}")

    fhir_map = fetch_all_video_summary_vs()

    # Load all JSON files and classify as existing or new
    valuesets = []
    for path in json_paths:
        with open(path, "r", encoding="utf-8") as f:
            vs = json.load(f)
        rules = vs.get("rulesToAddOrUpdate", vs.get("rules", []))
        clean_rules = [{"codeSystem": r["codeSystem"], "code": r["code"], "mapType": r["mapType"]} for r in rules]
        vs_id = fhir_map.get(vs["name"])
        valuesets.append({
            "name": vs["name"],
            "domain": vs["domain"],
            "scope": vs.get("scope", ""),
            "inclusionCriteria": vs.get("inclusionCriteria", ""),
            "exclusionCriteria": vs.get("exclusionCriteria", ""),
            "rules": clean_rules,
            "vs_id": vs_id,
            "is_existing": vs_id is not None,
        })

    existing_count = sum(1 for v in valuesets if v["is_existing"])
    new_count = len(valuesets) - existing_count
    print(f"Loaded {len(valuesets)} value set(s): {existing_count} existing (will update), {new_count} new (will create)")
    for vs in valuesets:
        tag = f"UPDATE vsId={vs['vs_id']}" if vs["is_existing"] else "NEW"
        print(f"  [{tag}] {vs['name']} ({len(vs['rules'])} rules)")

    # Step 1: Create/draft value sets + push rules
    results = []
    failed = []

    for idx, vs in enumerate(valuesets, 1):
        print(f"\n[{idx}/{len(valuesets)}] {vs['name']} ({len(vs['rules'])} rules)")

        vs_id, vsv_id = _get_or_create_vs(vs, fhir_map)
        if vs_id is None:
            failed.append(vs["name"])
            continue

        if vs["is_existing"]:
            _update_vs_metadata(vs_id, vsv_id, vs)
            _delete_stale_rules(vs_id, vsv_id, vs["rules"])
        _push_rules_in_batches(vs_id, vsv_id, vs["rules"], config.PS_BATCH_SIZE)
        _set_version_attribute(vs_id, vsv_id)

        results.append({
            "name": vs["name"],
            "domain": vs["domain"],
            "valueSetId": vs_id,
            "valueSetVersionId": vsv_id,
            "ruleCount": len(vs["rules"]),
        })

    # Steps 2+3: Trigger expansion + publish in parallel
    n_workers = min(MAX_PUBLISH_WORKERS, len(results))
    print(f"\n{'='*60}")
    print(f"EXPANDING & PUBLISHING ({n_workers} workers)")
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = {executor.submit(_expand_and_publish_one, r): r for r in results}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                r = futures[future]
                logger.warning("Expand+publish worker failed for %s: %s", r["name"], e)

    # Summary
    print(f"\n{'='*60}")
    print("PUBLISH COMPLETE")
    published = sum(1 for r in results if r.get("published"))
    print(f"  Published: {published}/{len(results)}, Failed: {len(failed)}")
    for r in results:
        status = "Published" if r.get("published") else "NOT published"
        print(f"  {r['name']}: vsId={r['valueSetId']}, rules={r['ruleCount']}, output={r.get('outputCount', '?')}, {status}")
    if failed:
        print(f"\n  Failed to create: {', '.join(failed)}")

    return results


def _get_or_create_vs(vs: Dict, existing_vs: Dict) -> tuple:
    """Returns (vs_id, vsv_id) or (None, None) on failure."""

    if vs["name"] in existing_vs:
        existing_id = existing_vs[vs["name"]]
        resp = graphql(QUERY_VS, {"valueSetId": existing_id})

        if resp.get("data") is None or resp["data"].get("valueSet") is None:
            print(f"  Existing vsId={existing_id} not found, creating new...")
            return _create_new_vs(vs)

        vsv = resp["data"]["valueSet"]["valueSetVersion"]
        print(f"  Existing: vsId={existing_id}, version={vsv['version']}, status={vsv['versionStatus']}")

        if vsv["versionStatus"] == "Draft":
            print(f"  Using existing draft: vsvId={vsv['valueSetVersionId']}, version={vsv['version']}")
            return existing_id, vsv["valueSetVersionId"]
        else:
            resp = graphql(DRAFT_MUTATION, {"valueSetId": existing_id, "versionId": vsv["valueSetVersionId"]})
            if resp.get("data") is None:
                err = resp.get("errors", [{}])[0].get("message", "Unknown error")
                print(f"  FAILED to create draft — {err}")
                return None, None
            new_vsv = resp["data"]["createValueSetDraft"]["valueSet"]["valueSetVersion"]
            print(f"  New draft: vsvId={new_vsv['valueSetVersionId']}, version={new_vsv['version']}")
            return existing_id, new_vsv["valueSetVersionId"]
    else:
        return _create_new_vs(vs)


def _update_vs_metadata(vs_id: int, vsv_id: int, vs: Dict) -> None:
    """Update scope, inclusionCriteria, exclusionCriteria on an existing draft version."""
    resp = graphql(METADATA_MUTATION, {"input": {
        "valueSetId": vs_id,
        "valueSetVersionId": vsv_id,
        "scope": vs.get("scope", ""),
        "inclusionCriteria": vs.get("inclusionCriteria", ""),
        "exclusionCriteria": vs.get("exclusionCriteria", ""),
    }})
    if resp.get("data") is None:
        err = (resp.get("errors") or [{}])[0].get("message", "Unknown error")
        print(f"  WARNING: metadata update failed — {err}")
    else:
        print(f"  Metadata updated (scope, inclusionCriteria, exclusionCriteria)")


def _fhir_search_by_name(name: str) -> Optional[int]:
    """Search PS FHIR for a VS by exact title. Returns vsId or None."""
    try:
        token = get_token()
        resp = requests.get(
            f"{config.PS_FHIR_URL}/ValueSet/search",
            params={"searchText": name, "pageSize": 20, "page": 1},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        resp.raise_for_status()
        for entry in resp.json().get("entry", []):
            res = entry.get("resource", {})
            if res.get("title") == name and res.get("id"):
                return int(res["id"])
    except Exception as e:
        logger.warning("FHIR name search failed for '%s': %s", name, e)
    return None


def _create_new_vs(vs: Dict) -> tuple:
    """Create a brand new value set. Returns (vs_id, vsv_id) or (None, None).
    If the VS already exists (e.g. from a crashed prior run), recovers via FHIR name search."""
    resp = graphql(CREATE_MUTATION, {"input": {
        "name": vs["name"],
        "domain": vs["domain"],
        "scope": vs["scope"],
        "inclusionCriteria": vs["inclusionCriteria"],
        "exclusionCriteria": vs["exclusionCriteria"],
    }})
    if resp.get("data") is None:
        err = resp.get("errors", [{}])[0].get("message", "Unknown error")
        if "already exists" in err.lower():
            # VS was created in a previous run but missed by FHIR/name lookup (scope not set).
            # Recover by finding it via FHIR name search and drafting it.
            vs_id = _fhir_search_by_name(vs["name"])
            if vs_id:
                print(f"  Already exists (vsId={vs_id}), recovering draft...")
                resp2 = graphql(QUERY_VS, {"valueSetId": vs_id})
                if resp2.get("data") and resp2["data"].get("valueSet"):
                    vsv = resp2["data"]["valueSet"]["valueSetVersion"]
                    if vsv["versionStatus"] == "Draft":
                        print(f"  Reusing existing draft: vsvId={vsv['valueSetVersionId']}")
                        return vs_id, vsv["valueSetVersionId"]
                    resp3 = graphql(DRAFT_MUTATION, {"valueSetId": vs_id, "versionId": vsv["valueSetVersionId"]})
                    if resp3.get("data"):
                        new_vsv = resp3["data"]["createValueSetDraft"]["valueSet"]["valueSetVersion"]
                        print(f"  New draft: vsvId={new_vsv['valueSetVersionId']}, version={new_vsv['version']}")
                        return vs_id, new_vsv["valueSetVersionId"]
        print(f"  FAILED — {err}")
        return None, None
    vs_data = resp["data"]["createNewValueSet"]["valueSet"]
    vs_id = vs_data["valueSetId"]
    vsv_id = vs_data["valueSetVersion"]["valueSetVersionId"]
    print(f"  Created: vsId={vs_id}, vsvId={vsv_id}")
    return vs_id, vsv_id


def republish_existing_valuesets(json_paths: List[str]) -> List[Dict]:
    """
    For all value sets in json_paths:
      - VSes found in PS (via FHIR lookup) → create new draft + update rules + publish
      - VSes not in PS                     → create brand new VS + push rules + publish
    """
    print(f"\n{'='*60}")
    print("REPUBLISH EXISTING VALUE SETS")
    print(f"{'='*60}")

    fhir_map = fetch_all_video_summary_vs()

    # Split into existing (republish) and new (create+publish)
    existing_valuesets = []
    new_valuesets = []
    for path in json_paths:
        with open(path, "r", encoding="utf-8") as f:
            vs = json.load(f)
        rules = vs.get("rulesToAddOrUpdate", vs.get("rules", []))
        clean_rules = [{"codeSystem": r["codeSystem"], "code": r["code"], "mapType": r["mapType"]} for r in rules]
        vs_data = {
            "name": vs["name"],
            "domain": vs["domain"],
            "scope": vs.get("scope", ""),
            "inclusionCriteria": vs.get("inclusionCriteria", ""),
            "exclusionCriteria": vs.get("exclusionCriteria", ""),
            "rules": clean_rules,
        }
        vs_id = fhir_map.get(vs["name"])
        if vs_id:
            vs_data["vs_id"] = vs_id
            existing_valuesets.append(vs_data)
        else:
            new_valuesets.append(vs_data)

    # Detect orphaned VSes — in PS but no matching JSON in this run
    json_names = {vs["name"] for vs in existing_valuesets + new_valuesets}
    orphans = {title: vsid for title, vsid in fhir_map.items() if title not in json_names}
    if orphans:
        print(f"\n-- ORPHANED VALUE SETS (in PS but no JSON generated) --")
        print(f"   Please DELETE these manually from the Precision Sets UI:")
        for name, vsid in orphans.items():
            print(f"   vsId={vsid}  {name}")

    print(f"\nFound {len(existing_valuesets)} to republish, {len(new_valuesets)} new to publish")
    for vs in new_valuesets:
        print(f"  [NEW] {vs['name']} ({len(vs['rules'])} rules)")

    results = []
    failed = []

    # Step 1a: Republish existing — create draft + push rules
    for idx, vs in enumerate(existing_valuesets, 1):
        vs_id = vs["vs_id"]
        print(f"\n[{idx}/{len(existing_valuesets)}] {vs['name']} (vsId={vs_id}, {len(vs['rules'])} rules)")

        resp = graphql(QUERY_VS, {"valueSetId": vs_id})
        if resp.get("data") is None or resp["data"].get("valueSet") is None:
            print(f"  FAILED — could not fetch value set vsId={vs_id}")
            failed.append(vs["name"])
            continue

        vsv = resp["data"]["valueSet"]["valueSetVersion"]
        print(f"  Current: vsvId={vsv['valueSetVersionId']}, version={vsv['version']}, status={vsv['versionStatus']}")

        _log_rules_diff(vs_id, vs["rules"])

        if vsv["versionStatus"] == "Draft":
            vsv_id = vsv["valueSetVersionId"]
            print(f"  Reusing existing draft: vsvId={vsv_id}")
        else:
            new_vsv = None
            for attempt in range(1, 4):
                try:
                    resp = graphql(DRAFT_MUTATION, {"valueSetId": vs_id, "versionId": vsv["valueSetVersionId"]})
                    if resp.get("data") is not None:
                        new_vsv = resp["data"]["createValueSetDraft"]["valueSet"]["valueSetVersion"]
                        break
                    err = (resp.get("errors") or [{}])[0].get("message", "Unknown error")
                    print(f"  Draft attempt {attempt} failed — {err}")
                except Exception as e:
                    print(f"  Draft attempt {attempt} error — {e}")
                if attempt < 3:
                    time.sleep(10)
            if new_vsv is None:
                print(f"  FAILED to create draft after 3 attempts")
                failed.append(vs["name"])
                continue
            vsv_id = new_vsv["valueSetVersionId"]
            print(f"  New draft: vsvId={vsv_id}, version={new_vsv['version']}")

        _update_vs_metadata(vs_id, vsv_id, vs)
        _delete_stale_rules(vs_id, vsv_id, vs["rules"])
        _push_rules_in_batches(vs_id, vsv_id, vs["rules"], config.PS_BATCH_SIZE)
        _set_version_attribute(vs_id, vsv_id)
        results.append({"name": vs["name"], "domain": vs["domain"], "valueSetId": vs_id, "valueSetVersionId": vsv_id, "ruleCount": len(vs["rules"])})

    # Step 1b: Publish new value sets
    for idx, vs in enumerate(new_valuesets, 1):
        print(f"\n[NEW {idx}/{len(new_valuesets)}] {vs['name']} ({len(vs['rules'])} rules)")
        vs_id, vsv_id = _create_new_vs(vs)
        if vs_id is None:
            failed.append(vs["name"])
            continue
        # Delete any stale inherited rules — no-op for truly new VSes,
        # but removes old rules for VSes recovered from a crashed prior run.
        _delete_stale_rules(vs_id, vsv_id, vs["rules"])
        _push_rules_in_batches(vs_id, vsv_id, vs["rules"], config.PS_BATCH_SIZE)
        _set_version_attribute(vs_id, vsv_id)
        results.append({"name": vs["name"], "domain": vs["domain"], "valueSetId": vs_id, "valueSetVersionId": vsv_id, "ruleCount": len(vs["rules"])})

    # Steps 2+3: Trigger expansion + publish in parallel
    n_workers = min(MAX_PUBLISH_WORKERS, len(results))
    print(f"\n{'='*60}")
    print(f"EXPANDING & PUBLISHING ({n_workers} workers)")
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = {executor.submit(_expand_and_publish_one, r): r for r in results}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                r = futures[future]
                logger.warning("Expand+publish worker failed for %s: %s", r["name"], e)

    # Summary
    print(f"\n{'='*60}")
    published = sum(1 for r in results if r.get("published"))
    print(f"REPUBLISH COMPLETE: {published}/{len(results)} published, {len(failed)} failed")
    for r in results:
        status = "Published" if r.get("published") else "NOT published"
        print(f"  {r['name']}: vsId={r['valueSetId']}, rules={r['ruleCount']}, output={r.get('outputCount', '?')}, {status}")
    if failed:
        print(f"\n  Failed: {', '.join(failed)}")
    return results


def set_attributes_for_all(attributes: List[Dict]) -> None:
    """
    Set value set attributes on all Video Summary VSes in PS (found via FHIR lookup).
    Each attribute dict: {"attributeKey": str, "attributeValue": str, "displayOrder": int}
    Flow per VS: create draft → set attributes → check expansion → publish.
    """
    print(f"\n{'='*60}")
    print("SET VALUE SET ATTRIBUTES")
    print(f"  Attributes: {attributes}")
    print(f"{'='*60}")

    fhir_map = fetch_all_video_summary_vs()
    if not fhir_map:
        print("No Video Summary value sets found in PS.")
        return

    entries = [{"name": title, "valueSetId": vsid} for title, vsid in fhir_map.items()]
    failed = []

    for idx, entry in enumerate(entries, 1):
        vs_id = entry["valueSetId"]
        name = entry["name"]
        print(f"\n[{idx}/{len(entries)}] {name} (vsId={vs_id})")

        # Get current published version
        resp = graphql(QUERY_VS, {"valueSetId": vs_id})
        if resp.get("data") is None or resp["data"].get("valueSet") is None:
            print(f"  FAILED — could not fetch VS")
            failed.append(name)
            continue
        vsv = resp["data"]["valueSet"]["valueSetVersion"]
        print(f"  Current: vsvId={vsv['valueSetVersionId']}, version={vsv['version']}, status={vsv['versionStatus']}")

        # Create draft (or reuse existing)
        if vsv["versionStatus"] == "Draft":
            vsv_id = vsv["valueSetVersionId"]
            print(f"  Reusing existing draft: vsvId={vsv_id}")
        else:
            draft_resp = None
            for attempt in range(1, 4):
                try:
                    draft_resp = graphql(DRAFT_MUTATION, {"valueSetId": vs_id, "versionId": vsv["valueSetVersionId"]})
                    if draft_resp.get("data") is not None:
                        break
                    err = (draft_resp.get("errors") or [{}])[0].get("message", "Unknown")
                    print(f"  Draft attempt {attempt} failed — {err}")
                except Exception as e:
                    print(f"  Draft attempt {attempt} error — {e}")
                if attempt < 3:
                    time.sleep(10)
            if draft_resp is None or draft_resp.get("data") is None:
                print(f"  FAILED to create draft")
                failed.append(name)
                continue
            new_vsv = draft_resp["data"]["createValueSetDraft"]["valueSet"]["valueSetVersion"]
            vsv_id = new_vsv["valueSetVersionId"]
            print(f"  New draft: vsvId={vsv_id}, version={new_vsv['version']}")

        # Set attributes on draft
        attr_resp = graphql(ATTRIBUTES_MUTATION, {"input": {
            "valueSetId": vs_id,
            "valueSetVersionId": vsv_id,
            "valueSetAttributes": attributes,
            "outputAttributes": [],
        }})
        if attr_resp.get("errors"):
            err = attr_resp["errors"][0].get("message", "Unknown")
            print(f"  FAILED to set attributes — {err}")
            failed.append(name)
            continue
        set_attrs = (attr_resp.get("data", {}).get("updateValueSetVersionAttributes", {}) or {}).get("valueSetAttributes", [])
        print(f"  Attributes set: {[{a['attributeKey']: a['attributeValue']} for a in (set_attrs or [])]}")

        # Check/trigger expansion then publish
        status = _trigger_expansion(vs_id, vsv_id)
        if status.upper() != "COMPLETED":
            print(f"  SKIPPED publish (expansion={status})")
            failed.append(name)
            continue

        pub_resp = graphql(PUBLISH_MUTATION, {"valueSetId": vs_id})
        if pub_resp.get("data") is None and any(
            "already published" in (e.get("message", "")).lower()
            for e in pub_resp.get("errors", [])
        ):
            print(f"  Published: (already published)")
        else:
            pub_vsv = pub_resp["data"]["publishValueSet"]["valueSet"]["valueSetVersion"]
            print(f"  Published: version={pub_vsv['version']}, status={pub_vsv['versionStatus']}")

    print(f"\n{'='*60}")
    print(f"ATTRIBUTES COMPLETE: {len(entries) - len(failed)}/{len(entries)} updated")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
