from linkding_xvr_minimal.agent import build_cross_version_prompt_payload
from linkding_xvr_minimal.expel_rules import build_expel_prompt_payload


def _metadata_from_spec(spec):
    return dict((spec.metadata or {}).get("normalized_task") or {})


def summarize_xvr_coverage(specs, rulebook, limit=8, fail_on_empty=False):
    rows = []
    covered = 0
    missing_task_ids = []
    by_drift_type = {}
    for spec in specs:
        metadata = _metadata_from_spec(spec)
        payload = build_cross_version_prompt_payload(
            rulebook=rulebook,
            task_metadata=metadata,
            limit=limit,
            fail_on_empty=fail_on_empty,
        )
        selection = payload["selection"]
        selected_rule_ids = list(selection.get("selected_rule_ids") or [])
        drift_type = str(metadata.get("drift_type") or "unknown")
        by_drift_type.setdefault(drift_type, {"tasks": 0, "covered": 0})
        by_drift_type[drift_type]["tasks"] += 1
        if selected_rule_ids:
            covered += 1
            by_drift_type[drift_type]["covered"] += 1
        else:
            missing_task_ids.append(int(spec.task_id))
        rows.append(
            {
                "task_id": int(spec.task_id),
                "task_name": spec.task_name,
                "drift_type": drift_type,
                "selected_rule_ids": selected_rule_ids,
                "rulebook_path": selection.get("rulebook_path", ""),
                "selection_context": dict(selection.get("selection_context") or {}),
                "warning": selection.get("warning", ""),
            }
        )
    return {
        "covered": covered,
        "missing_task_ids": sorted(missing_task_ids),
        "by_drift_type": by_drift_type,
        "rows": rows,
    }


def summarize_expel_coverage(specs, expel_rulebook, limit=3, fidelity="minimal"):
    if not expel_rulebook:
        return {
            "covered": 0,
            "missing_task_ids": [],
            "fidelity": str(fidelity or "minimal"),
            "selected_rule_count_min": 0,
            "selected_rule_count_max": 0,
            "rows": [],
        }
    rows = []
    covered = 0
    missing_task_ids = []
    selected_counts = []
    for spec in specs:
        metadata = _metadata_from_spec(spec)
        payload = build_expel_prompt_payload(
            rulebook=expel_rulebook,
            task_metadata=metadata,
            limit=limit,
            fidelity=fidelity,
        )
        selection = payload["selection"]
        selected_rule_ids = list(selection.get("selected_rule_ids") or [])
        selected_counts.append(len(selected_rule_ids))
        if selected_rule_ids:
            covered += 1
        else:
            missing_task_ids.append(int(spec.task_id))
        rows.append(
            {
                "task_id": int(spec.task_id),
                "task_name": spec.task_name,
                "selected_rule_ids": selected_rule_ids,
                "rulebook_path": selection.get("rulebook_path", ""),
                "selection_context": dict(selection.get("selection_context") or {}),
                "fidelity": selection.get("fidelity", ""),
            }
        )
    return {
        "covered": covered,
        "missing_task_ids": sorted(missing_task_ids),
        "fidelity": str(fidelity or "minimal"),
        "selected_rule_count_min": min(selected_counts or [0]),
        "selected_rule_count_max": max(selected_counts or [0]),
        "rows": rows,
    }


def build_pipeline_report(specs, rulebook, expel_rulebook=None, limit=8, expel_limit=3, expel_fidelity="minimal", fail_on_empty=False):
    xvr = summarize_xvr_coverage(
        specs,
        rulebook,
        limit=limit,
        fail_on_empty=fail_on_empty,
    )
    expel = summarize_expel_coverage(
        specs,
        expel_rulebook,
        limit=expel_limit,
        fidelity=expel_fidelity,
    )
    return {
        "task_count": len(specs),
        "xvr": xvr,
        "expel": expel,
    }
