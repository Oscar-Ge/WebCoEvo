"""Conservative promotion decisions for candidate reflection rulebooks."""

from collections import Counter


def summarize_eval_comparison(baseline_eval_rows, candidate_eval_rows, delta_manifest=None):
    baseline = _index_eval_rows(baseline_eval_rows)
    candidate = _index_eval_rows(candidate_eval_rows)
    task_ids = sorted(set(baseline).union(set(candidate)))
    improved = []
    regressed = []
    invalid = []
    for task_id in task_ids:
        left = baseline.get(task_id, {})
        right = candidate.get(task_id, {})
        left_success = _success_value(left)
        right_success = _success_value(right)
        if not right or _looks_invalid(right):
            invalid.append(task_id)
        if left_success is False and right_success is True:
            improved.append(task_id)
        if left_success is True and right_success is False:
            regressed.append(task_id)

    buckets = dict((delta_manifest or {}).get("buckets") or {})
    bucket_regressions = {}
    for bucket, ids in buckets.items():
        id_set = set(int(value) for value in list(ids or []))
        bucket_regressions[str(bucket)] = sorted(id_set.intersection(set(regressed)))

    return {
        "schema_version": "webcoevo-xvr-eval-comparison-v1",
        "task_count": len(task_ids),
        "baseline_successes": sum(1 for task_id in task_ids if _success_value(baseline.get(task_id, {})) is True),
        "candidate_successes": sum(1 for task_id in task_ids if _success_value(candidate.get(task_id, {})) is True),
        "baseline_success_rate": _rate(
            sum(1 for task_id in task_ids if _success_value(baseline.get(task_id, {})) is True),
            len(task_ids),
        ),
        "candidate_success_rate": _rate(
            sum(1 for task_id in task_ids if _success_value(candidate.get(task_id, {})) is True),
            len(task_ids),
        ),
        "improved_task_ids": improved,
        "regressed_task_ids": regressed,
        "invalid_task_ids": invalid,
        "invalid_count": len(invalid),
        "bucket_regressions": bucket_regressions,
    }


def summarize_transition_artifact(transition_artifact):
    rows = list((transition_artifact or {}).get("rows") or [])
    valid_rows = [
        row
        for row in rows
        if str(row.get("validity") or "valid_for_mining") == "valid_for_mining"
    ]
    counts = Counter(str(row.get("transition") or "unknown") for row in rows)
    improved = sorted(int(row.get("task_id") or 0) for row in valid_rows if row.get("transition") == "saved")
    regressed = sorted(int(row.get("task_id") or 0) for row in valid_rows if row.get("transition") == "lost")
    baseline_successes = counts.get("both_success", 0) + counts.get("lost", 0)
    candidate_successes = counts.get("both_success", 0) + counts.get("saved", 0)
    invalid_count = len(rows) - len(valid_rows)
    return {
        "schema_version": "webcoevo-xvr-transition-decision-summary-v1",
        "task_count": len(rows),
        "valid_task_count": len(valid_rows),
        "transition_counts": dict(sorted(counts.items())),
        "baseline_successes": baseline_successes,
        "candidate_successes": candidate_successes,
        "baseline_success_rate": _rate(baseline_successes, len(valid_rows)),
        "candidate_success_rate": _rate(candidate_successes, len(valid_rows)),
        "improved_task_ids": [task_id for task_id in improved if task_id],
        "regressed_task_ids": [task_id for task_id in regressed if task_id],
        "invalid_count": invalid_count,
        "bucket_regressions": {},
    }


def decide_promotion(delta_report, focus20_report=None, heldout_report=None, verification_report=None):
    report = dict(delta_report or {})
    verification = dict(verification_report or {})
    reasons = []

    if verification and not bool(verification.get("ok", True)):
        reasons.append("verification_report_not_ok")
        return _decision("reject", reasons, report, verification, focus20_report, heldout_report)
    contract = verification.get("contract") if isinstance(verification.get("contract"), dict) else {}
    if contract and not bool(contract.get("ok", True)):
        reasons.append("rulebook_contract_failed")
        return _decision("reject", reasons, report, verification, focus20_report, heldout_report)

    task_count = int(report.get("task_count") or report.get("valid_task_count") or 0)
    invalid_count = int(report.get("invalid_count") or 0)
    if task_count and float(invalid_count) / float(task_count) >= 0.5:
        reasons.append("infra_or_invalid_rows_dominate")
        return _decision("fix_infrastructure", reasons, report, verification, focus20_report, heldout_report)

    regressed = list(report.get("regressed_task_ids") or [])
    bucket_regressions = dict(report.get("bucket_regressions") or {})
    rail_regressions = []
    for bucket in ["must_keep", "regression_rails"]:
        rail_regressions.extend(list(bucket_regressions.get(bucket) or []))
    if regressed or rail_regressions or _has_regressions(focus20_report) or _has_regressions(heldout_report):
        reasons.append("candidate_regressed_saved_or_rail_rows")
        return _decision("iterate", reasons, report, verification, focus20_report, heldout_report)

    improved = list(report.get("improved_task_ids") or [])
    if improved:
        reasons.append("candidate_improved_target_rows_without_regression")
        return _decision("promote", reasons, report, verification, focus20_report, heldout_report)

    baseline_rate = float(report.get("baseline_success_rate") or 0.0)
    candidate_rate = float(report.get("candidate_success_rate") or 0.0)
    if baseline_rate >= 0.9 and candidate_rate >= 0.9:
        reasons.append("success_already_high_and_stable")
        return _decision("harden_environment", reasons, report, verification, focus20_report, heldout_report)

    reasons.append("no_clear_promotion_signal")
    return _decision("iterate", reasons, report, verification, focus20_report, heldout_report)


def render_promotion_decision_md(decision):
    row = dict(decision or {})
    lines = [
        "# Reflection Rulebook Promotion Decision",
        "",
        "Decision: {}".format(row.get("decision", "")),
        "",
        "Reasons:",
    ]
    for reason in list(row.get("reasons") or []):
        lines.append("- {}".format(reason))
    report = dict(row.get("delta_report") or {})
    if report:
        lines.extend(
            [
                "",
                "Summary:",
                "- task_count: {}".format(report.get("task_count", 0)),
                "- improved_task_ids: {}".format(list(report.get("improved_task_ids") or [])),
                "- regressed_task_ids: {}".format(list(report.get("regressed_task_ids") or [])),
                "- invalid_count: {}".format(report.get("invalid_count", 0)),
            ]
        )
    return "\n".join(lines) + "\n"


def _decision(decision, reasons, delta_report, verification_report, focus20_report, heldout_report):
    return {
        "schema_version": "webcoevo-xvr-promotion-decision-v1",
        "decision": decision,
        "reasons": list(reasons or []),
        "delta_report": dict(delta_report or {}),
        "verification_ok": bool((verification_report or {}).get("ok", True)),
        "focus20_report": dict(focus20_report or {}),
        "heldout_report": dict(heldout_report or {}),
    }


def _index_eval_rows(rows):
    indexed = {}
    for row in list(rows or []):
        task_id = int(row.get("task_id") or 0)
        if task_id:
            indexed[task_id] = dict(row)
    return indexed


def _success_value(row):
    if not row or "success" not in row:
        return None
    return bool(row.get("success"))


def _looks_invalid(row):
    error = str(row.get("error") or row.get("error_type") or "").lower()
    return any(
        marker in error
        for marker in [
            "auth_session_failure",
            "setup failure",
            "reset_error",
            "parser_failure",
            "evaluator failure",
        ]
    )


def _has_regressions(report):
    row = dict(report or {})
    return bool(row.get("regressed_task_ids") or row.get("rail_regressions"))


def _rate(count, total):
    total = int(total or 0)
    if total <= 0:
        return 0.0
    return float(count or 0) / float(total)
