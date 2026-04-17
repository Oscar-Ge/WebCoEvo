"""Build matched transition artifacts from paired reflection-rule runs."""

import glob
import json
from pathlib import Path

from linkding_xvr_minimal.tasks import normalize_task_metadata


def load_jsonl(path_or_pattern):
    rows = []
    paths = _expand_paths(path_or_pattern)
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    rows.append(json.loads(stripped))
    return rows


def index_eval_rows(rows):
    indexed = {}
    for row in list(rows or []):
        task_id = _to_int(row.get("task_id"))
        if task_id:
            indexed[task_id] = dict(row)
    return indexed


def index_trace_rows(rows):
    indexed = {}
    for row in list(rows or []):
        task_id = _to_int(row.get("task_id"))
        if task_id:
            indexed.setdefault(task_id, []).append(dict(row))
    for task_id in indexed:
        indexed[task_id] = sorted(indexed[task_id], key=lambda row: _to_int(row.get("step")))
    return indexed


def short_trace_excerpt(rows, max_steps=6):
    excerpt = []
    for row in sorted(list(rows or []), key=lambda item: _to_int(item.get("step")))[: int(max_steps or 0)]:
        excerpt.append(
            {
                "step": _to_int(row.get("step")),
                "event": str(row.get("event") or ""),
                "action": str(row.get("action") or ""),
                "model_output": str(row.get("model_output") or ""),
                "url": str(row.get("url") or ""),
                "error": str(row.get("error") or ""),
                "final_answer": str(row.get("final_answer") or ""),
                "success_so_far": bool(row.get("success_so_far", False)),
            }
        )
    return excerpt


def classify_transition(left_success, right_success):
    if left_success is None and right_success is None:
        return "missing"
    if left_success is None:
        return "right_only"
    if right_success is None:
        return "left_only"
    if bool(left_success) and bool(right_success):
        return "both_success"
    if not bool(left_success) and bool(right_success):
        return "saved"
    if bool(left_success) and not bool(right_success):
        return "lost"
    return "both_fail"


def classify_invalid_reason(eval_row, trace_rows):
    error = str((eval_row or {}).get("error") or "").strip().lower()
    if any(
        marker in error
        for marker in [
            "auth_session_failure",
            "login bootstrap",
            "setup failure",
            "could not reveal login",
            "runtime failure",
            "port collision",
        ]
    ):
        return "runtime_or_setup_failure"
    if any(
        marker in error
        for marker in [
            "parser_failure",
            "parse failure",
            "action format",
            "could not parse action",
        ]
    ):
        return "parser_or_action_format"
    if any(
        marker in error
        for marker in [
            "reset failure",
            "evaluator failure",
            "evaluation failure",
            "assertion mismatch",
        ]
    ):
        return "reset_or_evaluator_failure"
    if not list(trace_rows or []):
        return "empty_trace"
    return ""


def build_transition_artifact(
    task_rows,
    left_eval_rows,
    left_trace_rows,
    right_eval_rows,
    right_trace_rows,
    left_label,
    right_label,
    task_file="",
):
    left_eval = index_eval_rows(left_eval_rows)
    right_eval = index_eval_rows(right_eval_rows)
    left_trace = index_trace_rows(left_trace_rows)
    right_trace = index_trace_rows(right_trace_rows)
    rows = []
    transition_counts = {}

    for task_row in list(task_rows or []):
        metadata = normalize_task_metadata(task_row)
        task_id = _to_int(metadata.get("task_id") or task_row.get("task_id"))
        left_row = left_eval.get(task_id, {})
        right_row = right_eval.get(task_id, {})
        left_success = _success_value(left_row)
        right_success = _success_value(right_row)
        left_invalid = classify_invalid_reason(left_row, left_trace.get(task_id, []))
        right_invalid = classify_invalid_reason(right_row, right_trace.get(task_id, []))
        invalid_reason = left_invalid or right_invalid
        transition = "invalid_for_mining" if invalid_reason else classify_transition(left_success, right_success)
        transition_counts[transition] = transition_counts.get(transition, 0) + 1
        rows.append(
            {
                "task_id": task_id,
                "source_task_id": _to_int(metadata.get("source_task_id")),
                "focus20_source_task_id": _to_int(metadata.get("focus20_source_task_id")),
                "family": str(metadata.get("family") or ""),
                "source_family": str(metadata.get("source_family") or ""),
                "variant": str(metadata.get("variant") or ""),
                "drift_type": str(metadata.get("drift_type") or ""),
                "intent": str(task_row.get("intent") or ""),
                "intent_template": str(task_row.get("intent_template") or ""),
                "start_url": str(metadata.get("start_url") or ""),
                "left_label": str(left_label or ""),
                "right_label": str(right_label or ""),
                "left_success": bool(left_success) if left_success is not None else None,
                "right_success": bool(right_success) if right_success is not None else None,
                "left_steps": _to_int(left_row.get("steps")),
                "right_steps": _to_int(right_row.get("steps")),
                "left_error": str(left_row.get("error") or ""),
                "right_error": str(right_row.get("error") or ""),
                "transition": transition,
                "validity": "invalid_for_mining" if invalid_reason else "valid_for_mining",
                "invalid_reason": invalid_reason,
                "left_eval": dict(left_row),
                "right_eval": dict(right_row),
                "left_trace_excerpt": short_trace_excerpt(left_trace.get(task_id, [])),
                "right_trace_excerpt": short_trace_excerpt(right_trace.get(task_id, [])),
            }
        )

    return {
        "schema_version": "webcoevo-xvr-transitions-v1",
        "comparison": {
            "left_label": str(left_label or ""),
            "right_label": str(right_label or ""),
            "task_file": str(task_file or ""),
        },
        "summary": {
            "num_rows": len(rows),
            "transition_counts": dict(sorted(transition_counts.items())),
        },
        "rows": rows,
    }


def _expand_paths(path_or_pattern):
    raw = str(path_or_pattern)
    matches = [Path(path) for path in sorted(glob.glob(raw))]
    if matches:
        return matches
    path = Path(raw)
    if path.exists():
        return [path]
    raise FileNotFoundError("No JSONL file matched: {}".format(path_or_pattern))


def _success_value(row):
    if not row:
        return None
    if "success" not in row:
        return None
    return bool(row.get("success"))


def _to_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
