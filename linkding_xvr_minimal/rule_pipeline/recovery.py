def extract_failed_then_success_cases(recovery_payload):
    cases = []
    for task in recovery_payload.get("tasks", []) or []:
        failures = []
        success_episode = None
        success_attempt_index = None
        attempts = list(task.get("attempts", []) or [])
        for attempt in attempts:
            episode = attempt.get("episode") or {}
            if not episode:
                continue
            if bool(attempt.get("success")):
                if failures:
                    success_episode = dict(episode)
                    success_attempt_index = int(
                        attempt.get("attempt_index", episode.get("attempt_index", 0)) or 0
                    )
                    break
                continue
            failures.append(dict(episode))
        if not failures or success_episode is None:
            continue
        cases.append(
            {
                "task_id": int(task.get("task_id", 0)),
                "goal": str(task.get("goal", "") or ""),
                "version": str(task.get("version", "") or success_episode.get("version", "")),
                "failure_episodes": failures,
                "success_episode": success_episode,
                "success_attempt_index": success_attempt_index,
                "failure_attempt_count": len(failures),
            }
        )
    cases.sort(key=lambda row: int(row.get("task_id", 0)))
    return cases


def flatten_failed_then_success_episodes(cases):
    rows = []
    for case in cases:
        rows.extend(dict(episode) for episode in case.get("failure_episodes", []) or [])
        success_episode = case.get("success_episode") or {}
        if success_episode:
            rows.append(dict(success_episode))
    return rows


def build_recovery_artifact(episodes):
    grouped = {}
    for episode in list(episodes or []):
        task_id = int(episode.get("task_id", 0))
        version = str(episode.get("version", "") or "")
        goal = str(episode.get("goal", "") or "")
        key = (task_id, version, goal)
        grouped.setdefault(
            key,
            {
                "task_id": task_id,
                "goal": goal,
                "version": version,
                "attempts": [],
            },
        )
        grouped[key]["attempts"].append(
            {
                "attempt_index": int(episode.get("attempt_index", 0)),
                "success": bool(episode.get("success", False)),
                "episode": dict(episode),
            }
        )

    tasks = []
    for key in sorted(grouped):
        task = grouped[key]
        task["attempts"] = sorted(
            task["attempts"],
            key=lambda row: (
                int(row.get("attempt_index", 0)),
                str((row.get("episode") or {}).get("episode_id", "")),
            ),
        )
        tasks.append(task)

    cases = extract_failed_then_success_cases({"tasks": tasks})
    return {
        "schema_version": "webcoevo-recovery-artifact-v1",
        "summary": {
            "num_tasks": len(tasks),
            "num_failed_then_success_tasks": len(cases),
            "num_episodes": len(list(episodes or [])),
        },
        "tasks": tasks,
    }
