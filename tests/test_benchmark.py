from linkding_xvr_minimal.benchmark import build_task_metadata
from linkding_xvr_minimal.browser_task import compile_raw_task


def test_build_task_metadata_uses_normalized_fields():
    spec = compile_raw_task(
        {
            "sites": ["linkding"],
            "task_id": 1600501,
            "start_url": "http://localhost:9103/bookmarks/new",
            "intent": "goal",
            "instantiation_dict": {
                "version": "1.45.0",
                "family_id": "AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS",
                "focus20_source_task_id": 16005,
                "variant": "access",
                "drift_type": "access",
            },
        }
    )

    rows = build_task_metadata([spec])

    assert rows[0]["task_id"] == 1600501
    assert rows[0]["source_task_id"] == 16005
    assert rows[0]["focus20_source_task_id"] == 16005
    assert rows[0]["drift_type"] == "access"
    assert rows[0]["variant"] == "access"
    assert rows[0]["start_url"] == "http://localhost:9103/bookmarks/new"
