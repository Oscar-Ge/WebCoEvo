from pathlib import Path

from linkding_xvr_minimal.expel_rules import (
    build_expel_prompt_payload,
    load_expel_rules,
    render_expel_rules_block,
    select_expel_rules,
)


def test_load_expel_rules_accepts_dict_or_list_payload(tmp_path):
    dict_path = tmp_path / "dict_rules.json"
    dict_path.write_text(
        '{"rules": [{"rule_id": "r1", "text": "Use the local credentials."}]}',
        encoding="utf-8",
    )
    list_path = tmp_path / "list_rules.json"
    list_path.write_text(
        '[{"id": "r2", "rule": "Preserve the redirect."}]',
        encoding="utf-8",
    )

    dict_rules = load_expel_rules(dict_path)
    list_rules = load_expel_rules(list_path)

    assert dict_rules["path"] == str(dict_path)
    assert dict_rules["rules"][0]["rule_id"] == "r1"
    assert dict_rules["rules"][0]["text"] == "Use the local credentials."
    assert list_rules["rules"][0]["rule_id"] == "r2"
    assert list_rules["rules"][0]["text"] == "Preserve the redirect."


def test_select_expel_rules_prefers_matching_scope_then_global():
    rulebook = {
        "path": "inline.json",
        "rules": [
            {"rule_id": "global", "text": "Generic recovery."},
            {
                "rule_id": "runtime",
                "text": "Runtime only.",
                "scope": {"drift_types": ["runtime"]},
            },
            {
                "rule_id": "access",
                "text": "Access only.",
                "scope": {"drift_types": ["access"], "source_task_ids": [16005]},
                "confidence": 0.9,
            },
        ],
    }

    selection = select_expel_rules(
        rulebook,
        {
            "source_task_id": 16005,
            "focus20_source_task_id": 16005,
            "drift_type": "access",
            "variant": "access",
            "task_id": 1600501,
        },
        limit=2,
    )

    assert selection["selected_rule_ids"] == ["access", "global"]
    assert selection["rulebook_path"] == "inline.json"
    assert selection["selection_context"]["drift_type"] == "access"


def test_render_and_payload_use_legacy_injected_rule_fields():
    rulebook = {
        "path": "inline.json",
        "rules": [{"rule_id": "expel_login", "text": "Use baseline / Baseline123! for local login."}],
    }

    block = render_expel_rules_block(rulebook["rules"])
    payload = build_expel_prompt_payload(
        rulebook,
        {"task_id": 1600501, "source_task_id": 16005, "drift_type": "access"},
        limit=3,
    )

    assert "Task experience rules" in block
    assert "Use baseline / Baseline123!" in block
    assert "Task experience rules" in payload["prompt_block"]
    assert payload["extra_info"]["injected_rule_ids"] == ["expel_login"]
    assert payload["extra_info"]["injected_rule_texts"] == [
        "Use baseline / Baseline123! for local login."
    ]


def test_official_expel_memory_v2_official_eval_injects_full_rulebook():
    rulebook = load_expel_rules(
        Path(__file__).resolve().parents[1] / "rulebooks" / "expel_official_v2.json"
    )

    selection = select_expel_rules(
        rulebook,
        {
            "source_task_id": 16005,
            "focus20_source_task_id": 16005,
            "drift_type": "access",
            "variant": "access",
            "task_id": 1600501,
            "family": "AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS",
            "version": "1.45.0",
        },
        limit=3,
        fidelity="official_eval",
    )

    assert len(selection["selected_rule_ids"]) == 16
    assert selection["selected_rule_ids"][0] == "rule.1"
    assert selection["selected_rules"][-1]["rule_id"] == "rule.16"
