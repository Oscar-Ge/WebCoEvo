import json

from linkding_xvr_minimal.tasks import load_raw_tasks, normalize_task_metadata


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_collect_episodes_merges_trace_eval_and_task_metadata(tmp_path):
    from linkding_xvr_minimal.rule_pipeline.episodes import collect_episodes

    task_file = tmp_path / "tasks.json"
    task_file.write_text(
        json.dumps(
            [
                {
                    "task_id": 973001,
                    "intent": "Login and reach the home page.",
                    "intent_template": "login task",
                    "start_url": "http://localhost:9103/login",
                    "instantiation_dict": {
                        "version": "1.45.0",
                        "family": "AF20_ANCHOR_LOGIN_HOME",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    trace_file = tmp_path / "trace.jsonl"
    eval_file = tmp_path / "eval.jsonl"
    _write_jsonl(
        trace_file,
        [
            {
                "task_id": 973001,
                "version": "1.45.0",
                "step": 0,
                "event": "task_step",
                "action": "goto('http://localhost:9103/login')",
                "model_output": "Observe login form.",
                "url": "http://localhost:9103/login",
                "error": "",
                "final_answer": "",
                "success_so_far": False,
                "retry_guidance_text": "",
            },
            {
                "task_id": 973001,
                "version": "1.45.0",
                "step": 1,
                "event": "final_answer",
                "action": "send_msg_to_user('done')",
                "model_output": "Completed login flow.",
                "url": "http://localhost:9103/bookmarks",
                "error": "",
                "final_answer": "done",
                "success_so_far": True,
                "retry_guidance_text": "Preserve redirect after login.",
            },
        ],
    )
    _write_jsonl(
        eval_file,
        [
            {
                "task_id": 973001,
                "version": "1.45.0",
                "success": True,
                "error": "",
                "final_answer": "done",
                "steps": 2,
                "elapsed_sec": 1.5,
            }
        ],
    )

    episodes = collect_episodes(
        str(trace_file),
        str(eval_file),
        task_file=str(task_file),
        source_version="1.45.0",
    )

    assert len(episodes) == 1
    episode = episodes[0]
    assert episode["episode_id"] == "episode.973001.1_45_0"
    assert episode["task_id"] == 973001
    assert episode["source_version"] == "1.45.0"
    assert episode["version"] == "1.45.0"
    assert episode["family"] == "AF20_ANCHOR_LOGIN_HOME"
    assert episode["goal"] == "Login and reach the home page."
    assert episode["retry_guidance_text"] == "Preserve redirect after login."
    assert episode["steps_taken"] == 2
    assert episode["success"] is True
    assert len(episode["steps"]) == 2
    assert episode["trace_provenance"]["trace_file"].endswith("trace.jsonl")


def test_collect_episodes_official_full_assigns_attempt_indices_across_pairs(tmp_path):
    from linkding_xvr_minimal.rule_pipeline.episodes import collect_episodes

    task_file = tmp_path / "tasks.json"
    task_file.write_text(
        json.dumps(
            [
                {
                    "task_id": 1600501,
                    "intent": "Save prefilled bookmark.",
                    "intent_template": "save task",
                    "start_url": "http://localhost:9103/bookmarks/new",
                    "instantiation_dict": {
                        "version": "1.45.0",
                        "family": "TKB01_PREFILL_SAVE_AMBER",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    for idx, success in [(1, False), (2, True)]:
        _write_jsonl(
            tmp_path / f"trace_{idx}.jsonl",
            [
                {
                    "task_id": 1600501,
                    "version": "1.45.0",
                    "step": idx,
                    "event": "task_step",
                    "action": f"click('bid{idx}')",
                    "model_output": f"attempt {idx}",
                    "url": "http://localhost:9103/bookmarks/new",
                    "error": "" if success else "timeout",
                    "final_answer": "done" if success else "",
                    "success_so_far": success,
                    "retry_guidance_text": "",
                }
            ],
        )
        _write_jsonl(
            tmp_path / f"eval_{idx}.jsonl",
            [
                {
                    "task_id": 1600501,
                    "version": "1.45.0",
                    "success": success,
                    "error": "" if success else "timeout",
                    "final_answer": "done" if success else "",
                    "steps": 1,
                    "elapsed_sec": float(idx),
                }
            ],
        )

    episodes = collect_episodes(
        str(tmp_path / "trace_*.jsonl"),
        str(tmp_path / "eval_*.jsonl"),
        task_file=str(task_file),
        source_version="1.45.0",
        experience_fidelity="official_full",
    )

    assert len(episodes) == 2
    assert [episode["attempt_index"] for episode in episodes] == [0, 1]
    assert episodes[0]["trial_id"].startswith("trial.1.")
    assert episodes[1]["trial_id"].startswith("trial.2.")
    assert episodes[1]["success"] is True


def test_collect_episodes_reuses_normalized_task_metadata_from_real_config(tmp_path):
    from linkding_xvr_minimal.rule_pipeline.episodes import collect_episodes

    repo_root = __import__("pathlib").Path(__file__).resolve().parents[1]
    row = load_raw_tasks(repo_root / "configs" / "focus20_hardv3_smoke.raw.json")[0]
    metadata = normalize_task_metadata(row)
    task_file = tmp_path / "tasks.json"
    task_file.write_text(json.dumps([row]), encoding="utf-8")

    trace_file = tmp_path / "trace.jsonl"
    eval_file = tmp_path / "eval.jsonl"
    _write_jsonl(
        trace_file,
        [
            {
                "task_id": metadata["task_id"],
                "version": metadata["version"],
                "step": 0,
                "event": "task_step",
                "action": "observe()",
                "model_output": "Observe live page.",
                "url": metadata["start_url"],
                "error": "",
                "final_answer": "",
                "success_so_far": False,
                "retry_guidance_text": "",
            }
        ],
    )
    _write_jsonl(
        eval_file,
        [
            {
                "task_id": metadata["task_id"],
                "version": metadata["version"],
                "success": False,
                "error": "",
                "final_answer": "",
                "steps": 1,
                "elapsed_sec": 0.1,
            }
        ],
    )

    episodes = collect_episodes(
        str(trace_file),
        str(eval_file),
        task_file=str(task_file),
        source_version=metadata["version"],
    )

    assert len(episodes) == 1
    episode = episodes[0]
    assert episode["family"] == metadata["family"]
    assert episode["source_task_id"] == metadata["source_task_id"]
    assert episode["focus20_source_task_id"] == metadata["focus20_source_task_id"]
    assert episode["drift_type"] == metadata["drift_type"]
    assert episode["variant"] == metadata["variant"]
