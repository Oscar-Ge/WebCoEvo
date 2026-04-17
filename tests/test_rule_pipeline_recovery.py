def test_extract_failed_then_success_cases_only_keeps_tasks_with_failure_before_success():
    from linkding_xvr_minimal.rule_pipeline.recovery import extract_failed_then_success_cases

    payload = {
        "tasks": [
            {
                "task_id": 973802,
                "goal": "Recover login redirect.",
                "version": "1.45.0",
                "attempts": [
                    {
                        "success": False,
                        "attempt_index": 0,
                        "episode": {"episode_id": "episode.fail.1", "version": "1.45.0"},
                    },
                    {
                        "success": True,
                        "attempt_index": 1,
                        "episode": {"episode_id": "episode.success.1", "version": "1.45.0"},
                    },
                ],
            },
            {
                "task_id": 1600501,
                "goal": "Already succeeds.",
                "version": "1.45.0",
                "attempts": [
                    {
                        "success": True,
                        "attempt_index": 0,
                        "episode": {"episode_id": "episode.success.only", "version": "1.45.0"},
                    }
                ],
            },
        ]
    }

    cases = extract_failed_then_success_cases(payload)

    assert len(cases) == 1
    case = cases[0]
    assert case["task_id"] == 973802
    assert case["goal"] == "Recover login redirect."
    assert case["failure_attempt_count"] == 1
    assert case["success_attempt_index"] == 1
    assert case["failure_episodes"][0]["episode_id"] == "episode.fail.1"
    assert case["success_episode"]["episode_id"] == "episode.success.1"


def test_flatten_failed_then_success_episodes_preserves_failure_then_success_order():
    from linkding_xvr_minimal.rule_pipeline.recovery import (
        extract_failed_then_success_cases,
        flatten_failed_then_success_episodes,
    )

    payload = {
        "tasks": [
            {
                "task_id": 1601303,
                "goal": "Recover filtered query flow.",
                "version": "1.45.0",
                "attempts": [
                    {
                        "success": False,
                        "attempt_index": 0,
                        "episode": {"episode_id": "episode.fail.1", "version": "1.45.0"},
                    },
                    {
                        "success": False,
                        "attempt_index": 1,
                        "episode": {"episode_id": "episode.fail.2", "version": "1.45.0"},
                    },
                    {
                        "success": True,
                        "attempt_index": 2,
                        "episode": {"episode_id": "episode.success", "version": "1.45.0"},
                    },
                ],
            }
        ]
    }

    flattened = flatten_failed_then_success_episodes(extract_failed_then_success_cases(payload))

    assert [episode["episode_id"] for episode in flattened] == [
        "episode.fail.1",
        "episode.fail.2",
        "episode.success",
    ]
