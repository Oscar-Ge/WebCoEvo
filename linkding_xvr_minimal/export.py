import ast
import gzip
import json
import pickle
import time
from pathlib import Path


XVR_FIELDS = [
    "cross_version_reflection_rule_ids",
    "cross_version_reflection_rule_texts",
    "cross_version_reflection_rules_path",
    "cross_version_selection_context",
    "cross_version_rule_miss_reasons",
    "cross_version_warning",
]


def export_legacy_eval_rows(rows):
    out = []
    for row in rows:
        item = {
            "task_id": int(row["task_id"]),
            "version": row.get("version", "unknown"),
            "start_url": row.get("start_url", ""),
            "success": bool(row.get("success", False)),
            "steps": int(row.get("steps", 0)),
            "final_answer": row.get("final_answer", ""),
            "error": row.get("error", ""),
            "error_type": row.get("error_type", ""),
            "elapsed_sec": float(row.get("elapsed_sec", 0.0)),
            "variant": row.get("variant", ""),
            "drift_type": row.get("drift_type", ""),
            "candidate_rule_ids": list(row.get("candidate_rule_ids", [])),
            "injected_rule_ids": list(row.get("injected_rule_ids", [])),
            "retrieved_episode_ids": list(row.get("retrieved_episode_ids", [])),
            "dropped_rule_ids": list(row.get("dropped_rule_ids", [])),
            "rule_drop_reasons": dict(row.get("rule_drop_reasons", {})),
            "experience_representation": row.get("experience_representation", ""),
            "retry_guidance_text": row.get("retry_guidance_text", ""),
            "injected_rule_texts": list(row.get("injected_rule_texts", [])),
            "expel_rulebook_path": row.get("expel_rulebook_path", ""),
            "expel_selection_context": dict(row.get("expel_selection_context", {})),
            "expel_fidelity": row.get("expel_fidelity", ""),
            "rulebook_path": row.get("cross_version_reflection_rules_path", ""),
        }
        _copy_xvr_fields(item, row)
        out.append(item)
    return out


def export_legacy_trace_rows(rows):
    out = []
    for row in rows:
        item = {
            "task_id": int(row["task_id"]),
            "version": row.get("version", "unknown"),
            "step": int(row.get("step", 0)),
            "event": row.get("event", ""),
            "url": row.get("url", ""),
            "action": row.get("action", ""),
            "model_output": row.get("model_output", ""),
            "final_answer": row.get("final_answer", ""),
            "success_so_far": bool(row.get("success_so_far", False)),
            "error": row.get("error", ""),
            "error_type": row.get("error_type", ""),
            "variant": row.get("variant", ""),
            "drift_type": row.get("drift_type", ""),
            "candidate_rule_ids": list(row.get("candidate_rule_ids", [])),
            "injected_rule_ids": list(row.get("injected_rule_ids", [])),
            "retrieved_episode_ids": list(row.get("retrieved_episode_ids", [])),
            "injected_rule_texts": list(row.get("injected_rule_texts", [])),
            "dropped_rule_ids": list(row.get("dropped_rule_ids", [])),
            "rule_drop_reasons": dict(row.get("rule_drop_reasons", {})),
            "experience_representation": row.get("experience_representation", ""),
            "retry_guidance_text": row.get("retry_guidance_text", ""),
            "expel_rulebook_path": row.get("expel_rulebook_path", ""),
            "expel_selection_context": dict(row.get("expel_selection_context", {})),
            "expel_fidelity": row.get("expel_fidelity", ""),
            "rulebook_path": row.get("cross_version_reflection_rules_path", ""),
        }
        _copy_xvr_fields(item, row)
        out.append(item)
    return out


def build_reset_error_rows(task_metadata, error, preflight_extra_info):
    base = {
        "task_id": int(task_metadata.get("task_id", 0)),
        "version": task_metadata.get("version", "unknown"),
        "start_url": task_metadata.get("start_url", ""),
        "success": False,
        "steps": 0,
        "final_answer": "",
        "error": str(error or ""),
        "error_type": "reset_error",
        "elapsed_sec": 0.0,
        "injected_rule_ids": [],
    }
    for key, value in (preflight_extra_info or {}).items():
        base[key] = value
    trace = dict(base)
    trace.update(
        {
            "step": 0,
            "event": "reset_error",
            "url": task_metadata.get("start_url", ""),
            "action": "",
            "model_output": "",
            "success_so_far": False,
        }
    )
    return export_legacy_eval_rows([base])[0], export_legacy_trace_rows([trace])[0]


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_legacy_jsonl(output_dir, eval_rows, trace_rows, stem="uitars"):
    output_dir = Path(output_dir)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    eval_path = output_dir / "{}_eval_{}.jsonl".format(stem, timestamp)
    trace_path = output_dir / "{}_trace_{}.jsonl".format(stem, timestamp)
    write_jsonl(eval_path, export_legacy_eval_rows(eval_rows))
    write_jsonl(trace_path, export_legacy_trace_rows(trace_rows))
    return {"eval_path": eval_path, "trace_path": trace_path}


def export_agentlab_study_to_legacy_jsonl(
    study_dir,
    specs,
    output_dir,
    stem="uitars",
    preflight=None,
    expel_preflight=None,
):
    eval_rows, trace_rows = export_agentlab_study_to_rows(
        study_dir,
        specs,
        preflight=preflight,
        expel_preflight=expel_preflight,
    )
    return write_legacy_jsonl(output_dir, eval_rows, trace_rows, stem=stem)


def export_agentlab_study_to_rows(study_dir, specs, preflight=None, expel_preflight=None):
    try:
        from agentlab.experiments.loop import yield_all_exp_results
    except Exception as exc:
        raise RuntimeError("AgentLab export dependency is unavailable: {}".format(exc))

    spec_by_name = {}
    for spec in specs:
        spec_by_name[spec.task_name] = spec
        if spec.task_name.startswith("browsergym/"):
            spec_by_name[spec.task_name.split("/", 1)[1]] = spec

    eval_rows = []
    trace_rows = []
    preflight_extra = _preflight_extra_by_task_id(preflight, expel_preflight)
    for exp_result in yield_all_exp_results(Path(study_dir), progress_fn=None):
        task_name = exp_result.exp_args.env_args.task_name
        spec = spec_by_name.get(task_name)
        if spec is None:
            continue
        summary = exp_result.summary_info or {}
        steps = _load_steps(exp_result)
        success = bool(summary.get("cum_reward", 0.0) > 0.0 and not summary.get("err_msg"))
        last_extra = _last_extra_info(steps)
        error = str(summary.get("err_msg") or "")
        if not success and not error and bool(summary.get("truncated")):
            error = "max_steps_no_success"
        eval_row = {
            "task_id": spec.task_id,
            "version": spec.version,
            "start_url": spec.start_url,
            "variant": (spec.metadata or {}).get("normalized_task", {}).get("variant", ""),
            "drift_type": (spec.metadata or {}).get("normalized_task", {}).get("drift_type", ""),
            "success": success,
            "steps": int(summary.get("n_steps", len(steps)) or 0),
            "final_answer": _final_answer_from_steps(steps, success, spec),
            "error": error,
            "error_type": "agent_error" if error else "",
            "elapsed_sec": float(summary.get("stats.cum_step_elapsed") or 0.0),
        }
        eval_row.update(last_extra)
        eval_row = _with_preflight_rule_backfill(eval_row, preflight_extra)
        eval_rows.append(eval_row)
        if not steps:
            trace_row = {
                "task_id": spec.task_id,
                "version": spec.version,
                "step": 0,
                "event": "task_end",
                "url": spec.start_url,
                "action": "",
                "model_output": "",
                "final_answer": eval_row["final_answer"],
                "success_so_far": success,
                "error": error,
                "error_type": eval_row["error_type"],
                "variant": eval_row["variant"],
                "drift_type": eval_row["drift_type"],
            }
            trace_row.update(last_extra)
            trace_row = _with_preflight_rule_backfill(trace_row, preflight_extra)
            trace_rows.append(trace_row)
            continue
        success_so_far = False
        for step in steps:
            obs = step.obs or {}
            agent_info = step.agent_info or {}
            extra = agent_info.get("extra_info") or {}
            action = str(step.action or "")
            step_final = _parse_send_msg_action(action) or str(extra.get("final_answer") or "")
            success_so_far = success_so_far or bool(step.reward > 0 or (step.task_info or {}).get("success"))
            trace_row = {
                "task_id": spec.task_id,
                "version": spec.version,
                "step": int(step.step or 0),
                "event": "final_answer" if action.startswith("send_msg_to_user(") else "task_step",
                "url": str(obs.get("url") or spec.start_url) if isinstance(obs, dict) else spec.start_url,
                "action": action,
                "model_output": str(extra.get("raw_model_output") or agent_info.get("think") or ""),
                "final_answer": step_final,
                "success_so_far": success_so_far,
                "error": str(agent_info.get("err_msg") or (obs.get("last_action_error") if isinstance(obs, dict) else "") or ""),
                "error_type": "agent_error" if agent_info.get("err_msg") else "",
                "variant": (spec.metadata or {}).get("normalized_task", {}).get("variant", ""),
                "drift_type": (spec.metadata or {}).get("normalized_task", {}).get("drift_type", ""),
            }
            trace_row.update(extra)
            trace_row = _with_preflight_rule_backfill(trace_row, preflight_extra)
            trace_rows.append(trace_row)
    return export_legacy_eval_rows(eval_rows), export_legacy_trace_rows(trace_rows)


def _preflight_extra_by_task_id(preflight=None, expel_preflight=None):
    extra_by_task_id = {}
    for row in preflight or []:
        task_id = _safe_task_id(row.get("task_id"))
        if not task_id:
            continue
        extra = extra_by_task_id.setdefault(task_id, {})
        extra.update(
            {
                "cross_version_reflection_rule_ids": list(row.get("selected_rule_ids") or []),
                "cross_version_reflection_rules_path": row.get("rulebook_path", ""),
                "cross_version_selection_context": dict(row.get("selection_context") or {}),
                "cross_version_rule_miss_reasons": dict(row.get("miss_reasons") or {}),
                "cross_version_warning": row.get("warning", ""),
            }
        )
    for row in expel_preflight or []:
        task_id = _safe_task_id(row.get("task_id"))
        if not task_id:
            continue
        extra = extra_by_task_id.setdefault(task_id, {})
        extra.update(
            {
                "injected_rule_ids": list(row.get("selected_rule_ids") or []),
                "expel_rulebook_path": row.get("rulebook_path", ""),
                "expel_selection_context": dict(row.get("selection_context") or {}),
                "expel_fidelity": row.get("fidelity", ""),
            }
        )
    return extra_by_task_id


def _with_preflight_rule_backfill(row, preflight_extra_by_id):
    out = dict(row or {})
    task_id = _safe_task_id(out.get("task_id"))
    extra = dict((preflight_extra_by_id or {}).get(task_id) or {})
    for key, value in extra.items():
        if not out.get(key):
            out[key] = value
    if _is_reset_error(out.get("error", "")):
        out["error_type"] = "reset_error"
    return out


def _safe_task_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _is_reset_error(error):
    text = str(error or "")
    return any(
        token in text
        for token in (
            "ResetError",
            "reset_start_url_failed",
            "baseline_login_failed",
        )
    )


def _copy_xvr_fields(target, source):
    target["cross_version_reflection_rule_ids"] = list(
        source.get("cross_version_reflection_rule_ids", [])
    )
    target["cross_version_reflection_rule_texts"] = list(
        source.get("cross_version_reflection_rule_texts", [])
    )
    target["cross_version_reflection_rules_path"] = source.get(
        "cross_version_reflection_rules_path", ""
    )
    target["cross_version_selection_context"] = dict(
        source.get("cross_version_selection_context", {})
    )
    target["cross_version_rule_miss_reasons"] = dict(
        source.get("cross_version_rule_miss_reasons", {})
    )
    target["cross_version_warning"] = source.get("cross_version_warning", "")


def _load_steps(exp_result):
    try:
        return list(exp_result.steps_info)
    except Exception:
        pass
    exp_dir = getattr(exp_result, "exp_dir", None)
    if exp_dir is None:
        return []
    steps = []
    for path in sorted(Path(exp_dir).glob("step_*.pkl.gz")):
        with gzip.open(path, "rb") as handle:
            steps.append(pickle.load(handle))
    return steps


def _last_extra_info(steps):
    for step in reversed(steps or []):
        extra = dict(_agent_info_get(step.agent_info, "extra_info") or {})
        if extra:
            return extra
    return {}


def _agent_info_get(agent_info, key, default=None):
    if isinstance(agent_info, dict):
        return agent_info.get(key, default)
    return getattr(agent_info, key, default)


def _final_answer_from_steps(steps, success, spec):
    for step in reversed(steps or []):
        action_answer = _parse_send_msg_action(str(step.action or ""))
        if action_answer:
            return action_answer
        extra_answer = str(((step.agent_info or {}).get("extra_info") or {}).get("final_answer") or "").strip()
        if extra_answer:
            return extra_answer
    if success:
        return str((spec.state_check or {}).get("success_summary") or "")
    return ""


def _parse_send_msg_action(action):
    if not action.startswith("send_msg_to_user("):
        return ""
    try:
        return str(ast.literal_eval(action[len("send_msg_to_user(") : -1]))
    except Exception:
        return ""
