import json

from linkding_xvr_minimal.export import (
    _last_extra_info,
    _preflight_extra_by_task_id,
    _with_preflight_rule_backfill,
    build_reset_error_rows,
    export_legacy_eval_rows,
    export_legacy_trace_rows,
    write_jsonl,
)


def _row():
    return {
        "task_id": 1600501,
        "version": "1.45.0",
        "start_url": "http://localhost:9103/bookmarks/new",
        "success": False,
        "steps": 1,
        "final_answer": "",
        "error": "max_steps_no_success",
        "elapsed_sec": 1.5,
        "injected_rule_ids": ["expel_1"],
        "injected_rule_texts": ["Use local credentials."],
        "expel_rulebook_path": "expel.json",
        "expel_selection_context": {"drift_type": "access"},
        "expel_fidelity": "official_eval",
        "cross_version_reflection_rule_ids": ["xvr26_0004"],
        "cross_version_reflection_rule_texts": ["Preserve task-specific login next redirects"],
        "cross_version_reflection_rules_path": "rulebooks/v2_6.json",
        "cross_version_selection_context": {"source_task_id": 16005, "drift_type": "access"},
        "cross_version_rule_miss_reasons": {"xvr26_0001": "drift_type_mismatch"},
        "cross_version_warning": "",
        "variant": "access",
        "drift_type": "access",
    }


def test_eval_rows_include_cross_version_rule_ids_separately_from_expel_ids():
    rows = export_legacy_eval_rows([_row()])

    assert rows[0]["injected_rule_ids"] == ["expel_1"]
    assert rows[0]["injected_rule_texts"] == ["Use local credentials."]
    assert rows[0]["expel_rulebook_path"] == "expel.json"
    assert rows[0]["expel_fidelity"] == "official_eval"
    assert rows[0]["cross_version_reflection_rule_ids"] == ["xvr26_0004"]
    assert rows[0]["cross_version_reflection_rules_path"] == "rulebooks/v2_6.json"
    assert rows[0]["rulebook_path"] == "rulebooks/v2_6.json"
    assert rows[0]["variant"] == "access"
    assert rows[0]["drift_type"] == "access"


def test_trace_rows_include_xvr_audit_fields():
    row = _row()
    row.update({"step": 0, "event": "task_step", "url": row["start_url"], "action": "click('1')"})

    rows = export_legacy_trace_rows([row])

    assert rows[0]["cross_version_reflection_rule_ids"] == ["xvr26_0004"]
    assert rows[0]["cross_version_reflection_rule_texts"]
    assert rows[0]["cross_version_reflection_rules_path"] == "rulebooks/v2_6.json"
    assert rows[0]["cross_version_selection_context"]["source_task_id"] == 16005
    assert rows[0]["cross_version_rule_miss_reasons"]
    assert rows[0]["injected_rule_ids"] == ["expel_1"]
    assert rows[0]["expel_selection_context"]["drift_type"] == "access"
    assert rows[0]["rulebook_path"] == "rulebooks/v2_6.json"


def test_reset_error_rows_are_not_agent_failures():
    eval_row, trace_row = build_reset_error_rows(
        task_metadata={
            "task_id": 1600501,
            "version": "1.45.0",
            "start_url": "http://localhost:9103/bookmarks/new",
        },
        error="reset_start_url_failed",
        preflight_extra_info={
            "cross_version_reflection_rule_ids": ["xvr26_0004"],
            "cross_version_reflection_rules_path": "rulebooks/v2_6.json",
            "cross_version_selection_context": {"source_task_id": 16005, "drift_type": "access"},
        },
    )

    assert eval_row["steps"] == 0
    assert eval_row["error_type"] == "reset_error"
    assert trace_row["event"] == "reset_error"
    assert trace_row["cross_version_reflection_rule_ids"] == ["xvr26_0004"]


def test_write_jsonl_round_trips(tmp_path):
    path = tmp_path / "rows.jsonl"
    write_jsonl(path, [{"a": 1}, {"b": 2}])

    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert lines == [{"a": 1}, {"b": 2}]


def test_last_extra_info_uses_last_non_empty_agent_extra():
    class Step(object):
        def __init__(self, extra):
            self.agent_info = {"extra_info": extra}

    extra = {"cross_version_reflection_rule_ids": ["xvr26_0004"]}

    assert _last_extra_info([Step(extra), Step({})]) == extra


def test_preflight_backfill_adds_rule_audit_fields_to_reset_exception_rows():
    preflight = [
        {
            "task_id": 1500101,
            "selected_rule_ids": ["xvr24_0003"],
            "rulebook_path": "rulebooks/v2_4.json",
            "selection_context": {"drift_type": "access", "source_task_id": 0},
            "miss_reasons": {"xvr24_0001": "drift_type_mismatch"},
            "warning": "",
        }
    ]
    expel_preflight = [
        {
            "task_id": 1500101,
            "selected_rule_ids": ["rule.1", "rule.2"],
            "rulebook_path": "rulebooks/expel_official_v2.json",
            "selection_context": {"drift_type": "access"},
            "fidelity": "official_eval",
        }
    ]
    row = {
        "task_id": 1500101,
        "error": "Exception uncaught by agent or environment.\nResetError:\nbaseline_login_failed: Page.fill timeout",
        "error_type": "agent_error",
    }

    backfilled = _with_preflight_rule_backfill(
        row,
        _preflight_extra_by_task_id(preflight, expel_preflight),
    )

    assert backfilled["error_type"] == "reset_error"
    assert backfilled["cross_version_reflection_rule_ids"] == ["xvr24_0003"]
    assert backfilled["cross_version_reflection_rules_path"] == "rulebooks/v2_4.json"
    assert backfilled["cross_version_selection_context"]["drift_type"] == "access"
    assert backfilled["injected_rule_ids"] == ["rule.1", "rule.2"]
    assert backfilled["expel_rulebook_path"] == "rulebooks/expel_official_v2.json"
    assert backfilled["expel_fidelity"] == "official_eval"


def test_preflight_backfill_does_not_override_agent_reported_rule_fields():
    row = {
        "task_id": 1500101,
        "cross_version_reflection_rule_ids": ["agent_xvr"],
        "injected_rule_ids": ["agent_expel"],
    }
    preflight_extra = {
        1500101: {
            "cross_version_reflection_rule_ids": ["preflight_xvr"],
            "injected_rule_ids": ["preflight_expel"],
        }
    }

    backfilled = _with_preflight_rule_backfill(row, preflight_extra)

    assert backfilled["cross_version_reflection_rule_ids"] == ["agent_xvr"]
    assert backfilled["injected_rule_ids"] == ["agent_expel"]
