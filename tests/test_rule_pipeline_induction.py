from textwrap import dedent


def test_parse_rule_operations_accepts_only_supported_operations():
    from linkding_xvr_minimal.rule_pipeline.induction import parse_rule_operations

    operations = parse_rule_operations(
        dedent(
            """
            ADD: Preserve the login redirect after authentication.
            EDIT 1: Use one visible opener before falling back to a route.
            AGREE 2: Keep exact filtered-query evidence before apply.
            REMOVE 3: Repeat the same hidden click until it works.
            IGNORE: This should not be parsed.
            ADD: Missing terminal punctuation
            """
        )
    )

    assert operations == [
        ("ADD", "Preserve the login redirect after authentication."),
        ("EDIT 1", "Use one visible opener before falling back to a route."),
        ("AGREE 2", "Keep exact filtered-query evidence before apply."),
        ("REMOVE 3", "Repeat the same hidden click until it works."),
    ]


def test_update_rule_items_applies_add_agree_edit_and_remove_deterministically():
    from linkding_xvr_minimal.rule_pipeline.induction import update_rule_items

    rules = [("Use visible targets only.", 2), ("Preserve redirect.", 3)]
    updated = update_rule_items(
        rules,
        [
            ("AGREE 2", "Preserve redirect."),
            ("EDIT 1", "Use visible semantic targets only."),
            ("ADD", "Verify final evidence before apply."),
            ("REMOVE 2", "Preserve redirect."),
        ],
    )

    assert updated == [
        ("Preserve redirect.", 3),
        ("Use visible semantic targets only.", 3),
        ("Verify final evidence before apply.", 2),
    ]


def test_mine_specific_rules_from_cases_tracks_provenance_and_generation_records():
    from linkding_xvr_minimal.rule_pipeline.induction import mine_specific_rules_from_cases

    cases = [
        {
            "task_id": 9738,
            "goal": "Recover login redirect.",
            "failure_episodes": [
                {
                    "episode_id": "episode.9738.fail.0",
                    "task_id": 9738,
                    "goal": "Recover login redirect.",
                    "source_version": "1.45.0",
                    "version": "1.45.0",
                    "family": "AF20_LOGIN_REDIRECT",
                    "success": False,
                    "error": "timeout",
                    "steps": [
                        {
                            "step": 0,
                            "action": "click('old_bid')",
                            "model_output": "Retry stale click.",
                            "url": "http://localhost:9103/login",
                            "error": "timeout",
                        }
                    ],
                }
            ],
            "success_episode": {
                "episode_id": "episode.9738.success.1",
                "task_id": 9738,
                "goal": "Recover login redirect.",
                "source_version": "1.45.0",
                "version": "1.45.0",
                "family": "AF20_LOGIN_REDIRECT",
                "success": True,
                "error": "",
                "steps": [
                    {
                        "step": 1,
                        "action": "goto('/login/?next=/bookmarks')",
                        "model_output": "Preserve redirect.",
                        "url": "http://localhost:9103/login/?next=/bookmarks",
                        "error": "",
                    }
                ],
            },
        }
    ]

    def critique_fn(prompt):
        assert "Recover login redirect." in prompt
        return "ADD: Preserve task-specific login redirect parameters after authentication."

    rules, generation_records = mine_specific_rules_from_cases(
        cases,
        critique_fn=critique_fn,
        max_num_rules=5,
        success_critique_num=1,
    )

    assert len(rules) == 1
    rule = rules[0]
    assert rule["rule_id"] == "rule.1"
    assert rule["text"] == "Preserve task-specific login redirect parameters after authentication."
    assert rule["score"] >= 2
    assert rule["scope"] == "global"
    assert rule["scope_id"] == ""
    assert rule["source_task_ids"] == [9738]
    assert rule["provenance_episode_ids"] == [
        "episode.9738.fail.0",
        "episode.9738.success.1",
    ]
    assert rule["support_count"] == 2
    assert "mixed" in rule["evidence_mode"]

    assert len(generation_records) >= 1
    assert generation_records[0]["task_id"] == 9738
    assert generation_records[0]["operations"][0]["operation"] == "ADD"


def test_extract_insight_rows_deduplicates_by_task_summary_and_outcome():
    from linkding_xvr_minimal.rule_pipeline.induction import extract_insight_rows

    episodes = [
        {
            "task_id": 16005,
            "family": "TKB01_PREFILL_SAVE_AMBER",
            "goal": "Save prefilled bookmark.",
            "source_version": "1.45.0",
            "success": True,
            "error": "",
            "steps": [],
        },
        {
            "task_id": 16005,
            "family": "TKB01_PREFILL_SAVE_AMBER",
            "goal": "Save prefilled bookmark.",
            "source_version": "1.45.0",
            "success": True,
            "error": "",
            "steps": [],
        },
    ]

    def reflect_fn(_prompt):
        return [
            {
                "summary": "Preserve the prefilled title before save.",
                "when": "When a bookmark form is already populated.",
                "query_terms": ["prefilled", "save"],
            }
        ]

    insights = extract_insight_rows(episodes, reflect_fn=reflect_fn)

    assert len(insights) == 1
    assert insights[0]["summary"] == "Preserve the prefilled title before save."
    assert insights[0]["outcome_tag"] == "success"
