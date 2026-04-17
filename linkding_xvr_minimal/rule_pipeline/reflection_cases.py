"""Build compact mining cases for cross-version reflection-rule induction."""

import json
from pathlib import Path


GAP_DIAGNOSES = {
    "query_state_finalization_missed": {
        "observed_gap": "Exact query or filtered-state evidence is visible, but the agent keeps applying, clicking, or looping.",
        "must_preserve": "Finalize immediately when exact query, URL, or filtered-result evidence already satisfies the task.",
        "must_avoid": "Do not click Apply, Continue, noop, or route away after final query evidence is visible.",
    },
    "hidden_click_repeated": {
        "observed_gap": "A hidden or timed-out click target is retried instead of being discarded.",
        "must_preserve": "After one hidden click failure, re-observe and choose a different visible opener, route, or final answer.",
        "must_avoid": "Do not repeat the same hidden bid after a visibility or timeout failure.",
    },
    "login_next_lost": {
        "observed_gap": "A task-specific login next redirect or protected destination is lost after authentication.",
        "must_preserve": "Preserve next redirects, protected destinations, and prefilled values after login.",
        "must_avoid": "Do not strip the next parameter or return to a generic login page after successful authentication.",
    },
    "target_reached_but_no_final_answer": {
        "observed_gap": "Final task evidence is visible, but the agent keeps acting instead of answering.",
        "must_preserve": "Stop with a final answer when visible URL, heading, form, or result evidence satisfies the goal.",
        "must_avoid": "Do not enter noop, goto, or repeated-click loops after target evidence is visible.",
    },
    "noninteractive_mark_clicked": {
        "observed_gap": "The agent clicks a hidden input, CSRF token, divider, or generic non-interactive container.",
        "must_preserve": "Prefer visible semantic links, buttons, textboxes, and continuation controls.",
        "must_avoid": "Do not click hidden inputs, CSRF tokens, dividers, or non-interactive containers.",
    },
}


def build_diagnosis(row, gap_id):
    fallback = {
        "observed_gap": "The trace shows a reusable cross-version adaptation failure.",
        "must_preserve": "Preserve the successful behavior seen in matched trajectories.",
        "must_avoid": "Avoid overfitting to a single task row.",
    }
    return dict(GAP_DIAGNOSES.get(str(gap_id), fallback))


def build_mining_case(row, gap_id, left_label, right_label):
    task_id = int(row.get("task_id") or 0)
    return {
        "case_id": "gap.{}.{}".format(str(gap_id), task_id),
        "gap_id": str(gap_id),
        "task_metadata": {
            "task_id": task_id,
            "source_task_id": int(row.get("source_task_id") or 0),
            "focus20_source_task_id": int(row.get("focus20_source_task_id") or 0),
            "family": str(row.get("family") or ""),
            "variant": str(row.get("variant") or ""),
            "drift_type": str(row.get("drift_type") or ""),
            "intent": str(row.get("intent") or ""),
        },
        "transition": str(row.get("transition") or ""),
        "left_result": {
            "label": str(left_label or row.get("left_label") or ""),
            "success": bool(row.get("left_success")),
            "error": str(row.get("left_error") or ""),
            "trace_excerpt": _compact_trace(row.get("left_trace_excerpt")),
        },
        "right_result": {
            "label": str(right_label or row.get("right_label") or ""),
            "success": bool(row.get("right_success")),
            "error": str(row.get("right_error") or ""),
            "trace_excerpt": _compact_trace(row.get("right_trace_excerpt")),
        },
        "diagnosis": build_diagnosis(row, gap_id),
    }


def build_mining_cases(transition_artifact, behavior_gaps, max_cases_per_gap=5):
    rows_by_task_id = {
        int(row.get("task_id") or 0): row
        for row in list((transition_artifact or {}).get("rows") or [])
    }
    comparison = dict((transition_artifact or {}).get("comparison") or {})
    left_label = comparison.get("left_label", "")
    right_label = comparison.get("right_label", "")
    cases = []
    for gap in sorted(
        list((behavior_gaps or {}).get("gaps") or []),
        key=lambda item: (_priority_rank(item.get("priority")), str(item.get("gap_id") or "")),
    ):
        gap_id = str(gap.get("gap_id") or "")
        selected = 0
        for task_id in list(gap.get("supporting_task_ids") or []):
            row = rows_by_task_id.get(int(task_id))
            if not row:
                continue
            cases.append(build_mining_case(row, gap_id, left_label, right_label))
            selected += 1
            if selected >= int(max_cases_per_gap or 0):
                break
    return cases


def write_jsonl(path, rows):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in list(rows or [])),
        encoding="utf-8",
    )


def _compact_trace(rows, max_steps=6):
    out = []
    for row in list(rows or [])[: int(max_steps or 0)]:
        out.append(
            {
                "step": int(row.get("step") or 0),
                "action": str(row.get("action") or ""),
                "model_output": str(row.get("model_output") or ""),
                "url": str(row.get("url") or ""),
                "error": str(row.get("error") or ""),
                "final_answer": str(row.get("final_answer") or ""),
            }
        )
    return out


def _priority_rank(priority):
    return {"high": 0, "medium": 1, "low": 2}.get(str(priority or ""), 3)
