import json
from collections import Counter
from pathlib import Path

from linkding_xvr_minimal.tasks import (
    KNOWN_DRIFT_TYPES,
    filter_tasks,
    load_raw_tasks,
    normalize_task_metadata,
    rewrite_task_start_urls,
)


ROOT = Path(__file__).resolve().parents[1]


def test_focus20_source_task_id_is_promoted_to_source_task_id(tmp_path):
    raw_task = {
        "task_id": 1600501,
        "start_url": "http://localhost:9103/bookmarks/new",
        "instantiation_dict": {
            "version": "1.45.0",
            "family_id": "AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS",
            "focus20_source_task_id": 16005,
            "variant": "access",
            "drift_type": "access",
        },
    }
    task_file = tmp_path / "tasks.json"
    task_file.write_text(json.dumps([raw_task]), encoding="utf-8")

    rows = load_raw_tasks(task_file)
    metadata = normalize_task_metadata(rows[0])

    assert metadata["task_id"] == 1600501
    assert metadata["source_task_id"] == 16005
    assert metadata["focus20_source_task_id"] == 16005
    assert metadata["drift_type"] == "access"
    assert metadata["variant"] == "access"
    assert metadata["source_family"] == "AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS"
    assert metadata["family"] == "AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS"
    assert metadata["version"] == "1.45.0"
    assert metadata["start_url"] == "http://localhost:9103/bookmarks/new"


def test_top_level_values_take_precedence_over_nested_instantiation():
    raw_task = {
        "task_id": 973001,
        "source_task_id": "9730",
        "focus20_source_task_id": "9730",
        "source_family": "TOP_SOURCE_FAMILY",
        "family": "TOP_FAMILY",
        "variant": "surface",
        "drift_type": "surface",
        "version": "1.45.0-hardv3",
        "start_url": "http://localhost:9107/login?next=/bookmarks",
        "instantiation_dict": {
            "source_task_id": 111,
            "focus20_source_task_id": 222,
            "family_id": "NESTED_FAMILY",
            "variant": "access",
            "drift_type": "access",
            "version": "nested",
        },
    }

    metadata = normalize_task_metadata(raw_task)

    assert metadata == {
        "task_id": 973001,
        "source_task_id": 9730,
        "focus20_source_task_id": 9730,
        "drift_type": "surface",
        "variant": "surface",
        "source_family": "TOP_SOURCE_FAMILY",
        "family": "TOP_FAMILY",
        "version": "1.45.0-hardv3",
        "start_url": "http://localhost:9107/login?next=/bookmarks",
    }


def test_variant_falls_back_to_drift_type_when_known_drift_type():
    raw_task = {
        "task_id": 1601601,
        "start_url": "http://localhost:9112/tags",
        "instantiation_dict": {
            "version": "1.45.0",
            "focus20_source_task_id": 16016,
            "family_id": "AF20_ROUTE_TAGS_TO_SETTINGS",
            "variant": "structural",
        },
    }

    metadata = normalize_task_metadata(raw_task)

    assert metadata["variant"] == "structural"
    assert metadata["drift_type"] == "structural"
    assert metadata["drift_type"] in KNOWN_DRIFT_TYPES


def test_filter_tasks_uses_normalized_metadata():
    rows = [
        {
            "task_id": 1,
            "start_url": "http://localhost:1",
            "instantiation_dict": {"variant": "access", "focus20_source_task_id": 10},
        },
        {
            "task_id": 2,
            "start_url": "http://localhost:2",
            "instantiation_dict": {"variant": "runtime", "focus20_source_task_id": 20},
        },
        {
            "task_id": 3,
            "start_url": "http://localhost:3",
            "instantiation_dict": {"variant": "access", "focus20_source_task_id": 30},
        },
    ]

    filtered = filter_tasks(rows, task_id=None, limit=1, variant="access", drift_type=None)

    assert [row["task_id"] for row in filtered] == [1]


def test_rewrite_task_start_urls_retargets_variants_to_runtime_hosts():
    rows = [
        {
            "task_id": 1600501,
            "start_url": "http://localhost:9103/login?next=/bookmarks/new",
            "instantiation_dict": {"variant": "access", "focus20_source_task_id": 16005},
        },
        {
            "task_id": 1600502,
            "start_url": "http://localhost:9108/login?next=/bookmarks/new",
            "instantiation_dict": {"variant": "runtime", "focus20_source_task_id": 16005},
        },
    ]

    rewritten = rewrite_task_start_urls(
        rows,
        {
            "access": "http://127.0.0.1:9303",
            "runtime": "http://127.0.0.1:9308",
        },
        variants=["access", "runtime"],
    )

    assert [row["task_id"] for row in rewritten] == [1600501, 1600502]
    assert rewritten[0]["start_url"].startswith("http://127.0.0.1:9303/login")
    assert rewritten[1]["start_url"].startswith("http://127.0.0.1:9308/login")


def test_focus20_full_config_matches_main_repo_68_row_hardv3_probe():
    rows = load_raw_tasks(ROOT / "configs" / "focus20_hardv3_full.raw.json")
    counts = Counter(normalize_task_metadata(row)["drift_type"] for row in rows)

    assert len(rows) == 68
    assert counts == {
        "access": 13,
        "surface": 13,
        "content": 9,
        "runtime": 16,
        "process": 6,
        "structural": 6,
        "functional": 5,
    }
