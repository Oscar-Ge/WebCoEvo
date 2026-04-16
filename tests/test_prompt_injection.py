import pytest

from linkding_xvr_minimal.agent import (
    build_cross_version_prompt_payload,
    build_expel_prompt_payload,
)
from linkding_xvr_minimal.prompting import build_hardv3_task_guidance, build_text_only_action_prompt
from linkding_xvr_minimal.rulebook import load_rulebook


class FakeActionSet(object):
    def describe(self, with_long_description=False):
        return "click(bid), fill(bid, value), send_msg_to_user(text)"


def test_text_prompt_contains_goal_and_action_contract():
    prompt = build_text_only_action_prompt(
        obs={"pruned_html": "<button bid='a1'>Login</button>", "url": "http://localhost:9103/login"},
        goal="Sign in",
        action_set=FakeActionSet(),
        observation_char_limit=1000,
    )

    assert "Sign in" in prompt["content"]
    assert "exactly one BrowserGym action" in prompt["content"]
    assert "click('a314')" in prompt["content"]


def test_cross_version_prompt_payload_separates_xvr_ids_from_expel_ids():
    rulebook = {
        "path": "inline.json",
        "rules": [
            {
                "rule_id": "xvr_inline",
                "title": "Inline rule",
                "scope": {"drift_types": ["access"]},
                "adaptation_strategy": ["Use the visible login continuation."],
            }
        ],
    }

    payload = build_cross_version_prompt_payload(
        rulebook=rulebook,
        task_metadata={
            "task_id": 1600501,
            "source_task_id": 16005,
            "focus20_source_task_id": 16005,
            "drift_type": "access",
            "variant": "access",
        },
        limit=8,
        fail_on_empty=True,
    )

    assert "Cross-version adaptation rules" in payload["prompt_block"]
    assert payload["extra_info"]["injected_rule_ids"] == []
    assert payload["extra_info"]["cross_version_reflection_rule_ids"] == ["xvr_inline"]
    assert payload["extra_info"]["cross_version_reflection_rules_path"] == "inline.json"
    assert payload["extra_info"]["cross_version_selection_context"]["source_task_id"] == 16005
    assert payload["extra_info"]["cross_version_selection_context"]["focus20_source_task_id"] == 16005


def test_cross_version_prompt_payload_reports_empty_selection():
    rulebook = {
        "path": "inline.json",
        "rules": [{"rule_id": "xvr_runtime", "scope": {"drift_types": ["runtime"]}}],
    }
    metadata = {
        "task_id": 1600501,
        "source_task_id": 16005,
        "focus20_source_task_id": 16005,
        "drift_type": "access",
        "variant": "access",
    }

    payload = build_cross_version_prompt_payload(
        rulebook=rulebook,
        task_metadata=metadata,
        limit=8,
        fail_on_empty=False,
    )
    assert payload["extra_info"]["cross_version_reflection_rule_ids"] == []
    assert payload["extra_info"]["cross_version_rule_miss_reasons"]
    assert payload["extra_info"]["cross_version_warning"]

    with pytest.raises(ValueError):
        build_cross_version_prompt_payload(
            rulebook=rulebook,
            task_metadata=metadata,
            limit=8,
            fail_on_empty=True,
        )


def test_v26_rulebook_payload_is_non_empty_for_smoke_access():
    rulebook = load_rulebook("rulebooks/v2_6.json")

    payload = build_cross_version_prompt_payload(
        rulebook=rulebook,
        task_metadata={
            "task_id": 1600501,
            "source_task_id": 16005,
            "focus20_source_task_id": 16005,
            "drift_type": "access",
            "variant": "access",
        },
        limit=8,
        fail_on_empty=True,
    )

    assert payload["extra_info"]["cross_version_reflection_rule_ids"]


def test_expel_and_xvr_payloads_keep_rule_ids_separate():
    expel_payload = build_expel_prompt_payload(
        {
            "path": "expel.json",
            "rules": [{"rule_id": "expel_login", "text": "Use local baseline credentials."}],
        },
        {"task_id": 1600501, "source_task_id": 16005, "drift_type": "access"},
        limit=3,
    )
    xvr_payload = build_cross_version_prompt_payload(
        {
            "path": "xvr.json",
            "rules": [
                {
                    "rule_id": "xvr_access",
                    "title": "Preserve login redirects",
                    "scope": {"drift_types": ["access"]},
                    "adaptation_strategy": ["Preserve next redirects."],
                }
            ],
        },
        {"task_id": 1600501, "source_task_id": 16005, "drift_type": "access"},
        limit=8,
    )

    assert "Task experience rules" in expel_payload["prompt_block"]
    assert expel_payload["extra_info"]["injected_rule_ids"] == ["expel_login"]
    assert expel_payload["extra_info"]["cross_version_reflection_rule_ids"] == []
    assert xvr_payload["extra_info"]["injected_rule_ids"] == []
    assert xvr_payload["extra_info"]["cross_version_reflection_rule_ids"] == ["xvr_access"]


def test_hardv3_guidance_tells_agent_to_open_review_checkpoint_once():
    guidance = build_hardv3_task_guidance(
        obs={
            "url": "http://127.0.0.1:9103/bookmarks/new?url=https%3A%2F%2Fexample.com%2Ffocus20%2Flogin-prefill-tagged&title=Focus20%20Login%20Prefill%20Tagged&tag_names=focus20-login",
            "axtree_txt": "[165] button 'Review editable fields'",
            "pruned_html": "<button bid='165'>Review editable fields</button>",
        },
        task_metadata={
            "task_id": 1600501,
            "source_task_id": 16005,
            "focus20_source_task_id": 16005,
            "drift_type": "access",
            "variant": "access",
            "family": "AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS",
        },
    )

    assert "Review editable fields" in guidance
    assert "Do not noop" in guidance


def test_hardv3_guidance_tells_agent_to_fill_missing_tag_then_finish():
    guidance = build_hardv3_task_guidance(
        obs={
            "url": "http://127.0.0.1:9103/bookmarks/new?url=https%3A%2F%2Fexample.com%2Ffocus20%2Flogin-prefill-tagged&title=Focus20%20Login%20Prefill%20Tagged&tag_names=focus20-login&hardv3_release_ready=1",
            "axtree_txt": "\n".join(
                [
                    "[204] textbox 'URL' value='https://example.com/focus20/login-prefill-tagged'",
                    "[211] textbox 'Tags'",
                    "[222] textbox 'Title' value='Focus20 Login Prefill Tagged'",
                    "[243] button 'Save'",
                ]
            ),
            "pruned_html": "\n".join(
                [
                    "<input bid='204' id='id_url' value='https://example.com/focus20/login-prefill-tagged'/>",
                    "<input bid='211' id='id_tag_string' value=''/>",
                    "<input bid='222' id='id_title' value='Focus20 Login Prefill Tagged'/>",
                ]
            ),
        },
        task_metadata={
            "task_id": 1600501,
            "source_task_id": 16005,
            "focus20_source_task_id": 16005,
            "drift_type": "access",
            "variant": "access",
            "family": "AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS",
        },
    )

    assert "focus20-login" in guidance
    assert "Tags field" in guidance
    assert "send_msg_to_user" in guidance


def test_hardv3_form_guidance_ignores_hidden_checkpoint_script_text():
    guidance = build_hardv3_task_guidance(
        obs={
            "url": "http://127.0.0.1:9103/bookmarks/new?url=https%3A%2F%2Fexample.com%2Ffocus20%2Flogin-prefill-tagged&title=Focus20%20Login%20Prefill%20Tagged&tag_names=focus20-login&hardv3_release_ready=1",
            "axtree_txt": "\n".join(
                [
                    "[204] textbox 'URL' value='https://example.com/focus20/login-prefill-tagged'",
                    "[211] textbox 'Tags'",
                    "[222] textbox 'Title' value='Focus20 Login Prefill Tagged'",
                ]
            ),
            "pruned_html": "\n".join(
                [
                    "<script>const buttonLabel = 'Review editable fields';</script>",
                    "<input bid='211' id='id_tag_string' value=''/>",
                ]
            ),
        },
        task_metadata={
            "task_id": 1600501,
            "source_task_id": 16005,
            "focus20_source_task_id": 16005,
            "drift_type": "access",
            "variant": "access",
            "family": "AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS",
        },
    )

    assert "bookmark completion check" in guidance
    assert "bookmark checkpoint" not in guidance
