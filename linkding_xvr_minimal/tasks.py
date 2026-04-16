import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


KNOWN_DRIFT_TYPES = {
    "access",
    "content",
    "functional",
    "process",
    "runtime",
    "structural",
    "surface",
}


def load_raw_tasks(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        rows = payload.get("rows") or payload.get("tasks") or []
    else:
        rows = payload
    if not isinstance(rows, list):
        raise ValueError("task file must contain a JSON list or an object with rows/tasks")
    return [dict(row) for row in rows if isinstance(row, dict)]


def _instantiation(row):
    value = row.get("instantiation_dict") or {}
    return value if isinstance(value, dict) else {}


def _first_text(*values):
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _first_int(*values):
    for value in values:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 0


def _normalize_drift_type(row, inst):
    drift_type = _first_text(row.get("drift_type"), inst.get("drift_type")).lower()
    if drift_type:
        return drift_type
    variant = _first_text(row.get("variant"), inst.get("variant")).lower()
    if variant in KNOWN_DRIFT_TYPES:
        return variant
    return ""


def normalize_task_metadata(row):
    inst = _instantiation(row)
    task_id = _first_int(row.get("task_id"), inst.get("task_id"))
    focus20_source_task_id = _first_int(
        row.get("focus20_source_task_id"),
        inst.get("focus20_source_task_id"),
    )
    source_task_id = _first_int(
        row.get("source_task_id"),
        inst.get("source_task_id"),
        focus20_source_task_id,
    )
    if not focus20_source_task_id:
        focus20_source_task_id = source_task_id

    variant = _first_text(row.get("variant"), inst.get("variant")).lower()
    drift_type = _normalize_drift_type(row, inst)
    family = _first_text(
        row.get("family"),
        row.get("family_id"),
        inst.get("family"),
        inst.get("family_id"),
    )
    source_family = _first_text(
        row.get("source_family"),
        row.get("source_family_id"),
        inst.get("source_family"),
        inst.get("source_family_id"),
        family,
    )

    return {
        "task_id": task_id,
        "source_task_id": source_task_id,
        "focus20_source_task_id": focus20_source_task_id,
        "drift_type": drift_type,
        "variant": variant,
        "source_family": source_family,
        "family": family,
        "version": _first_text(row.get("version"), inst.get("version")),
        "start_url": _first_text(row.get("start_url"), inst.get("start_url")),
    }


def filter_tasks(rows, task_id=None, limit=None, variant=None, drift_type=None):
    filtered = []
    variant = str(variant or "").strip().lower()
    drift_type = str(drift_type or "").strip().lower()
    task_id = int(task_id or 0)
    limit = int(limit or 0)

    for row in rows:
        metadata = normalize_task_metadata(row)
        if task_id and metadata["task_id"] != task_id:
            continue
        if variant and metadata["variant"] != variant:
            continue
        if drift_type and metadata["drift_type"] != drift_type:
            continue
        filtered.append(row)
        if limit > 0 and len(filtered) >= limit:
            break
    return filtered


def build_smoke_subset(rows):
    selected = []
    seen = set()
    for drift_type in ("access", "surface", "content", "runtime", "process", "structural", "functional"):
        for row in rows:
            metadata = normalize_task_metadata(row)
            if metadata["drift_type"] == drift_type and drift_type not in seen:
                selected.append(row)
                seen.add(drift_type)
                break
    return selected


def rewrite_task_start_urls(rows, variant_host_map, variants=None, limit=0):
    selected_variants = {
        str(value or "").strip().lower()
        for value in (variants or [])
        if str(value or "").strip()
    }
    out = []
    for row in rows:
        metadata = normalize_task_metadata(row)
        variant = metadata["variant"] or metadata["drift_type"]
        variant = str(variant or "").strip().lower()
        if selected_variants and variant not in selected_variants:
            continue
        host_url = str((variant_host_map or {}).get(variant) or "").strip()
        if not host_url:
            continue
        parsed_src = urlsplit(metadata["start_url"] or row.get("start_url") or "")
        parsed_host = urlsplit(host_url)
        updated = dict(row)
        updated["start_url"] = urlunsplit(
            (
                parsed_host.scheme,
                parsed_host.netloc,
                parsed_src.path,
                parsed_src.query,
                parsed_src.fragment,
            )
        )
        out.append(updated)
        if limit and len(out) >= int(limit):
            break
    return out
