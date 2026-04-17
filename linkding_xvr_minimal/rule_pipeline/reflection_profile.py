"""Aggregate matched transition artifacts into reflection capability profiles."""


def group_transition_rows(rows, group_by):
    groups = {}
    for row in list(rows or []):
        value = str(row.get(group_by) or "unknown")
        group = groups.setdefault(
            value,
            {
                "group_by": str(group_by),
                "group_value": value,
                "tasks": 0,
                "valid_tasks": 0,
                "invalid_count": 0,
                "left_successes": 0,
                "right_successes": 0,
                "transition_counts": {},
                "task_ids": [],
            },
        )
        group["tasks"] += 1
        group["task_ids"].append(int(row.get("task_id") or 0))
        if str(row.get("validity") or "valid_for_mining") == "invalid_for_mining":
            group["invalid_count"] += 1
        else:
            group["valid_tasks"] += 1
            if bool(row.get("left_success")):
                group["left_successes"] += 1
            if bool(row.get("right_success")):
                group["right_successes"] += 1
        transition = str(row.get("transition") or "unknown")
        group["transition_counts"][transition] = group["transition_counts"].get(transition, 0) + 1

    for group in groups.values():
        group["task_ids"] = sorted(set(group["task_ids"]))
        group["transition_counts"] = dict(sorted(group["transition_counts"].items()))
        valid_tasks = int(group.get("valid_tasks") or 0)
        group["left_success_rate"] = _rate(group["left_successes"], valid_tasks)
        group["right_success_rate"] = _rate(group["right_successes"], valid_tasks)
        group["status"] = label_capability(
            group["right_successes"],
            valid_tasks,
            invalid_count=group["invalid_count"],
        )
        group["recommended_next_action"] = recommend_next_action(group)
    return groups


def label_capability(successes, total, invalid_count=0):
    total = int(total or 0)
    invalid_count = int(invalid_count or 0)
    if total <= 0 and invalid_count > 0:
        return "invalid_for_mining"
    if total <= 0:
        return "cannot_do"
    rate = float(successes or 0) / float(total)
    if rate >= 0.8:
        return "can_do"
    if rate <= 0.2:
        return "cannot_do"
    return "borderline"


def recommend_next_action(group):
    status = str(group.get("status") or "")
    transitions = dict(group.get("transition_counts") or {})
    right_success_rate = float(group.get("right_success_rate") or 0.0)
    if status == "invalid_for_mining":
        return "fix_infrastructure"
    if status == "can_do" and right_success_rate >= 0.9:
        return "harden_environment"
    if transitions.get("lost") or transitions.get("both_fail") or status in set(["borderline", "cannot_do"]):
        return "repair_rules"
    return "hold_steady"


def build_capability_profile(transition_artifact, group_bys=("drift_type", "variant", "source_task_id")):
    rows = list((transition_artifact or {}).get("rows") or [])
    groups = []
    for group_by in list(group_bys or []):
        grouped = group_transition_rows(rows, group_by)
        groups.extend(grouped[key] for key in sorted(grouped))
    return {
        "schema_version": "webcoevo-xvr-capability-profile-v1",
        "comparison": dict((transition_artifact or {}).get("comparison") or {}),
        "summary": {
            "num_rows": len(rows),
            "group_count": len(groups),
        },
        "groups": groups,
    }


def _rate(successes, total):
    total = int(total or 0)
    if total <= 0:
        return 0.0
    return float(successes or 0) / float(total)
