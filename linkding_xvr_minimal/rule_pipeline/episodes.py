import glob
import json
from pathlib import Path

from linkding_xvr_minimal.tasks import normalize_task_metadata


def _expand_jsonl_paths(path_or_pattern):
    raw = str(path_or_pattern)
    matches = [Path(path) for path in sorted(glob.glob(raw))]
    if matches:
        return matches
    path = Path(raw)
    if path.exists():
        return [path]
    raise FileNotFoundError("No JSONL file matched: {}".format(path_or_pattern))


def _load_jsonl(paths):
    rows = []
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                rows.append(json.loads(stripped))
    return rows


def _load_task_index(task_file):
    if not task_file:
        return {}
    rows = json.loads(Path(task_file).read_text(encoding="utf-8"))
    return {int(row["task_id"]): row for row in rows}


def _episode_key(task_id, version):
    return int(task_id), str(version or "unknown")


def _episode_id(task_id, version, trial_id=""):
    normalized = str(version or "unknown").replace(".", "_")
    suffix = ".{}".format(trial_id) if trial_id else ""
    return "episode.{}.{}{}".format(int(task_id), normalized, suffix)


def _collect_episode_batch(
    trace_paths,
    eval_paths,
    task_index,
    source_version,
    trial_id="",
):
    trace_rows = _load_jsonl(trace_paths)
    eval_rows = _load_jsonl(eval_paths)
    grouped_steps = {}
    for row in trace_rows:
        key = _episode_key(row.get("task_id", 0), row.get("version", "unknown"))
        grouped_steps.setdefault(key, []).append(
            {
                "step": int(row.get("step", 0)),
                "event": str(row.get("event", "")),
                "action": str(row.get("action", "")),
                "model_output": str(row.get("model_output", "")),
                "url": str(row.get("url", "")),
                "error": str(row.get("error", "")),
                "final_answer": str(row.get("final_answer", "")),
                "success_so_far": bool(row.get("success_so_far", False)),
                "retry_guidance_text": str(row.get("retry_guidance_text", "")),
            }
        )

    eval_index = {}
    for row in eval_rows:
        key = _episode_key(row.get("task_id", 0), row.get("version", "unknown"))
        eval_index[key] = row

    keys = sorted(set(grouped_steps) | set(eval_index))
    episodes = []
    for key in keys:
        task_id, version = key
        eval_row = eval_index.get(key, {})
        task_row = task_index.get(task_id, {})
        metadata = normalize_task_metadata(task_row) if task_row else {}
        steps = sorted(grouped_steps.get(key, []), key=lambda row: row["step"])
        retry_guidance_text = ""
        for step in steps:
            value = str(step.get("retry_guidance_text", "")).strip()
            if value:
                retry_guidance_text = value
                break
        episodes.append(
            {
                "episode_id": _episode_id(task_id, version, trial_id=trial_id),
                "task_id": task_id,
                "trial_id": trial_id,
                "attempt_index": 0,
                "source_version": str(source_version or metadata.get("version") or version or "unknown"),
                "version": str(version or metadata.get("version") or "unknown"),
                "family": str(metadata.get("family") or ""),
                "source_family": str(metadata.get("source_family") or ""),
                "source_task_id": int(metadata.get("source_task_id") or 0),
                "focus20_source_task_id": int(metadata.get("focus20_source_task_id") or 0),
                "drift_type": str(metadata.get("drift_type") or ""),
                "variant": str(metadata.get("variant") or ""),
                "goal": str(task_row.get("intent") or ""),
                "intent_template": str(task_row.get("intent_template") or ""),
                "start_url": str(metadata.get("start_url") or eval_row.get("start_url") or ""),
                "success": bool(eval_row.get("success", False)),
                "terminal_error": str(eval_row.get("error", "")),
                "error": str(eval_row.get("error", "")),
                "final_answer": str(eval_row.get("final_answer", "")),
                "steps_taken": int(eval_row.get("steps", len(steps))),
                "elapsed_sec": float(eval_row.get("elapsed_sec", 0.0)),
                "retry_guidance_text": retry_guidance_text,
                "steps": steps,
                "trace_provenance": {
                    "trace_file": ",".join(str(path) for path in trace_paths),
                    "eval_file": ",".join(str(path) for path in eval_paths),
                    "trial_id": trial_id,
                },
            }
        )
    return episodes


def collect_episodes(
    trace_path,
    eval_path,
    task_file=None,
    source_version="",
    experience_fidelity="alpha",
):
    trace_paths = _expand_jsonl_paths(trace_path)
    eval_paths = _expand_jsonl_paths(eval_path)
    task_index = _load_task_index(task_file)
    fidelity = str(experience_fidelity or "alpha")
    if fidelity != "official_full":
        return _collect_episode_batch(
            trace_paths=trace_paths,
            eval_paths=eval_paths,
            task_index=task_index,
            source_version=source_version,
        )

    if len(trace_paths) != len(eval_paths):
        raise ValueError("official_full collection requires matching trace/eval file counts")

    episodes = []
    attempt_counts = {}
    for pair_idx, pair in enumerate(zip(trace_paths, eval_paths), start=1):
        trace_file, eval_file = pair
        trial_id = "trial.{}.{}".format(pair_idx, eval_file.stem)
        batch = _collect_episode_batch(
            trace_paths=[trace_file],
            eval_paths=[eval_file],
            task_index=task_index,
            source_version=source_version,
            trial_id=trial_id,
        )
        for episode in batch:
            key = (int(episode.get("task_id", 0)), str(episode.get("version", "")))
            episode["attempt_index"] = int(attempt_counts.get(key, 0))
            attempt_counts[key] = int(episode["attempt_index"]) + 1
            episodes.append(episode)
    return episodes
