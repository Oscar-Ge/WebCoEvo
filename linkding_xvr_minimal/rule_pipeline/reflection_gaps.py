"""Mine behavior gaps from matched cross-version transition artifacts."""

import re


GAP_LABELS = {
    "hidden_click_repeated": "A hidden or timed-out click target is retried instead of discarded.",
    "query_state_finalization_missed": "Exact query or filtered-state evidence is visible, but the agent keeps applying or looping.",
    "login_next_lost": "A login next redirect or protected destination is lost after authentication.",
    "target_reached_but_no_final_answer": "Final task evidence is visible, but the agent does not stop with a final answer.",
    "noninteractive_mark_clicked": "The agent clicks a hidden input, CSRF token, divider, or generic non-interactive mark.",
}


def detect_gap_labels(row):
    if str(row.get("validity") or "valid_for_mining") == "invalid_for_mining":
        return []
    labels = set()
    right_steps = list(row.get("right_trace_excerpt") or [])
    all_steps = list(row.get("left_trace_excerpt") or []) + right_steps
    text = _joined_step_text(all_steps)
    right_text = _joined_step_text(right_steps)

    if _has_repeated_hidden_click(right_steps):
        labels.add("hidden_click_repeated")
    if _mentions_query_evidence(right_text) and (
        _has_apply_or_loop_after_evidence(right_steps)
        or any(str(step.get("final_answer") or "").strip() for step in right_steps)
    ):
        labels.add("query_state_finalization_missed")
    if _lost_login_next(row, right_steps):
        labels.add("login_next_lost")
    if _target_reached_without_final(right_steps):
        labels.add("target_reached_but_no_final_answer")
    if any(marker in text for marker in ["csrf", "hidden input", "divider", "generic container", "non-interactive"]):
        labels.add("noninteractive_mark_clicked")
    return sorted(labels)


def build_behavior_gaps(transition_artifact):
    gap_rows = {}
    for row in list((transition_artifact or {}).get("rows") or []):
        for gap_id in detect_gap_labels(row):
            gap = gap_rows.setdefault(
                gap_id,
                {
                    "gap_id": gap_id,
                    "label": GAP_LABELS.get(gap_id, gap_id),
                    "transition_mix": {},
                    "supporting_task_ids": set(),
                    "risk_task_ids": set(),
                    "recommended_rule_action": "edit_rule",
                    "priority": "medium",
                },
            )
            transition = str(row.get("transition") or "unknown")
            gap["transition_mix"][transition] = gap["transition_mix"].get(transition, 0) + 1
            task_id = int(row.get("task_id") or 0)
            if task_id:
                gap["supporting_task_ids"].add(task_id)
                if transition in set(["lost", "both_fail"]):
                    gap["risk_task_ids"].add(task_id)

    gaps = []
    for gap in gap_rows.values():
        gap["transition_mix"] = dict(sorted(gap["transition_mix"].items()))
        gap["supporting_task_ids"] = sorted(gap["supporting_task_ids"])
        gap["risk_task_ids"] = sorted(gap["risk_task_ids"])
        gap["priority"] = priority_for_gap(gap)
        gaps.append(gap)
    gaps.sort(key=lambda row: (_priority_rank(row.get("priority")), row.get("gap_id", "")))
    return {
        "schema_version": "webcoevo-xvr-behavior-gaps-v1",
        "summary": {
            "num_gaps": len(gaps),
            "num_transition_rows": len(list((transition_artifact or {}).get("rows") or [])),
        },
        "gaps": gaps,
    }


def priority_for_gap(gap):
    transitions = dict((gap or {}).get("transition_mix") or {})
    if transitions.get("lost") or transitions.get("both_fail", 0) >= 2:
        return "high"
    if transitions.get("saved"):
        return "medium"
    return "low"


def _priority_rank(priority):
    return {"high": 0, "medium": 1, "low": 2}.get(str(priority or ""), 3)


def _joined_step_text(steps):
    parts = []
    for step in steps:
        parts.extend(
            [
                str(step.get("action") or ""),
                str(step.get("model_output") or ""),
                str(step.get("url") or ""),
                str(step.get("error") or ""),
                str(step.get("final_answer") or ""),
            ]
        )
    return " ".join(parts).lower()


def _has_repeated_hidden_click(steps):
    seen = {}
    for step in steps:
        action = str(step.get("action") or "").strip()
        text = " ".join([action, str(step.get("error") or ""), str(step.get("model_output") or "")]).lower()
        if not action:
            continue
        if any(marker in text for marker in ["hidden", "not visible", "timed-out", "timeout", "not stable"]):
            seen[action] = seen.get(action, 0) + 1
    return any(count >= 2 for count in seen.values())


def _mentions_query_evidence(text):
    return bool(re.search(r"(query|filter|filtered|search).{0,40}(visible|present|exact|match|state|result)", text)) or "?query=" in text


def _has_apply_or_loop_after_evidence(steps):
    if not steps:
        return False
    for step in steps[1:]:
        action = str(step.get("action") or "").lower()
        if any(marker in action for marker in ["apply", "continue", "noop", "goto", "click"]):
            return True
    return False


def _lost_login_next(row, steps):
    start_url = str(row.get("start_url") or "").lower()
    if "next=" not in start_url and not any("next=" in str(step.get("url") or "").lower() for step in steps):
        return False
    urls = [str(step.get("url") or "").lower() for step in steps if str(step.get("url") or "").strip()]
    if not urls:
        return False
    return any("/login" in url and "next=" not in url for url in urls[1:])


def _target_reached_without_final(steps):
    saw_evidence = False
    for step in steps:
        text = " ".join(
            [
                str(step.get("model_output") or ""),
                str(step.get("url") or ""),
                str(step.get("error") or ""),
            ]
        ).lower()
        if bool(step.get("success_so_far")) or any(
            marker in text
            for marker in [
                "requested",
                "goal",
                "success state",
                "final evidence",
                "visible",
            ]
        ):
            saw_evidence = True
        if saw_evidence and str(step.get("final_answer") or "").strip():
            return False
        if saw_evidence and str(step.get("action") or "").strip().lower() in set(["noop", "goto", "click"]):
            return True
    return False
