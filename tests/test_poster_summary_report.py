import json
import re
from pathlib import Path

from linkding_xvr_minimal.reporting_poster_summary import (
    build_poster_summary,
    render_main_panel_svg,
    render_reflection_panel_svg,
    render_report_markdown,
)


def _make_umich_summary():
    return {
        "scenarios": {
            "control_1450": {
                "benchmarks": {
                    "focus20": {
                        "settings": {
                            "no_rules": {"successes": 9, "expected_total": 68, "overall_rate": 9 / 68},
                            "expel_only": {"successes": 56, "expected_total": 68, "overall_rate": 56 / 68},
                        }
                    },
                    "taskbank36": {
                        "settings": {
                            "no_rules": {"successes": 133, "expected_total": 167, "overall_rate": 133 / 167},
                            "expel_only": {"successes": 124, "expected_total": 167, "overall_rate": 124 / 167},
                        }
                    },
                }
            },
            "first_modified": {
                "benchmarks": {
                    "focus20": {
                        "settings": {
                            "expel_only": {"successes": 60, "expected_total": 68, "overall_rate": 60 / 68},
                            "v2_4": {"successes": 67, "expected_total": 68, "overall_rate": 67 / 68},
                        }
                    },
                    "taskbank36": {
                        "settings": {
                            "expel_only": {"successes": 114, "expected_total": 167, "overall_rate": 114 / 167},
                            "v2_4": {"successes": 143, "expected_total": 167, "overall_rate": 143 / 167},
                        }
                    },
                }
            },
        }
    }


def _make_hardv3_summary():
    return {
        "benchmarks": {
            "focus20_hardv3": {
                "settings": {
                    "expel_only": {"successes": 8, "overall_rate": 8 / 68},
                    "v2_4": {"successes": 65, "overall_rate": 65 / 68},
                    "v2_5": {"successes": 60, "overall_rate": 60 / 68},
                    "v2_6": {"successes": 60, "overall_rate": 60 / 68},
                    "v2_4_1": {"successes": 60, "overall_rate": 60 / 68},
                },
                "expected_total": 68,
            },
            "taskbank36_hardv3": {
                "settings": {
                    "expel_only": {"successes": 66, "overall_rate": 66 / 167},
                    "v2_4": {"successes": 97, "overall_rate": 97 / 167},
                    "v2_5": {"successes": 61, "overall_rate": 61 / 167},
                    "v2_6": {"successes": 82, "overall_rate": 82 / 167},
                    "v2_4_1": {"successes": 97, "overall_rate": 97 / 167},
                },
                "expected_total": 167,
            },
        }
    }


def test_build_poster_summary_normalizes_public_labels_and_best_series():
    summary = build_poster_summary(_make_umich_summary(), _make_hardv3_summary())

    assert list(summary["main_panels"].keys()) == [
        "training_task_sets_main",
        "heldout_validation_task_sets_main",
    ]
    assert list(summary["reflection_panels"].keys()) == [
        "training_task_sets_reflection_v3",
        "heldout_validation_task_sets_reflection_v3",
    ]

    training = summary["main_panels"]["training_task_sets_main"]
    assert training["title"] == "Training Task Sets"
    assert [point["label"] for point in training["website_versions"]] == [
        "Website V1",
        "Website V2",
        "Website V3",
    ]
    assert training["website_versions"][0]["series"]["no_rules"]["successes"] == 9
    assert training["website_versions"][1]["series"]["best_reflection_rules"]["public_version"] == "Reflection Rules V1"
    assert training["website_versions"][2]["series"]["best_reflection_rules"]["successes"] == 65

    training_reflection = summary["reflection_panels"]["training_task_sets_reflection_v3"]
    assert training_reflection["title"] == "Training Task Sets"
    assert training_reflection["subtitle"] == "Reflection Rules on Website V3"
    assert [item["label"] for item in training_reflection["series"]] == [
        "Reflection Rules V1",
        "Reflection Rules V2",
        "Reflection Rules V3",
        "Reflection Rules V4",
    ]

    heldout = summary["main_panels"]["heldout_validation_task_sets_main"]
    assert heldout["title"] == "Held-out Validation Task Sets"
    assert heldout["website_versions"][0]["series"]["expel_rules"]["successes"] == 124
    assert heldout["website_versions"][2]["series"]["best_reflection_rules"]["successes"] == 97
    assert heldout["website_versions"][2]["series"]["best_reflection_rules"]["public_version"] == "Reflection Rules V1 / V4"

    heldout_reflection = summary["reflection_panels"]["heldout_validation_task_sets_reflection_v3"]
    assert heldout_reflection["title"] == "Held-out Validation Task Sets"
    assert heldout_reflection["series"][0]["rate"] == 97 / 167
    assert heldout_reflection["series"][3]["is_best"] is True


def test_render_panel_svg_and_report_include_poster_labels(tmp_path):
    summary = build_poster_summary(_make_umich_summary(), _make_hardv3_summary())

    main_svg = render_main_panel_svg(summary["main_panels"]["training_task_sets_main"])
    training_reflection_svg = render_reflection_panel_svg(
        summary["reflection_panels"]["training_task_sets_reflection_v3"]
    )
    reflection_svg = render_reflection_panel_svg(
        summary["reflection_panels"]["heldout_validation_task_sets_reflection_v3"]
    )
    report = render_report_markdown(
        summary,
        {
            "training_task_sets_main": "../../figures/training_task_sets_main_poster_summary.svg",
            "training_task_sets_reflection_v3": "../../figures/training_task_sets_reflection_v3_poster_summary.svg",
            "heldout_validation_task_sets_main": "../../figures/heldout_validation_task_sets_main_poster_summary.svg",
            "heldout_validation_task_sets_reflection_v3": "../../figures/heldout_validation_task_sets_reflection_v3_poster_summary.svg",
        },
    )

    assert "Training Task Sets" in main_svg
    assert "ExpeL Rules" in main_svg
    assert "Best Reflection Rules" in main_svg
    assert "Website V1" in main_svg
    assert "Website V2" in main_svg
    assert "Website V3" in main_svg
    assert ">Original<" not in main_svg
    assert ">Transfer<" not in main_svg

    training_v3_best = re.search(r'y="([^"]+)" class="value" text-anchor="middle">95.6%</text>', main_svg)
    assert training_v3_best is not None
    assert float(training_v3_best.group(1)) < 150.0

    training_reflection_best = re.search(
        r'y="([^"]+)" class="value" text-anchor="middle">95.6%</text>',
        training_reflection_svg,
    )
    assert training_reflection_best is not None
    assert float(training_reflection_best.group(1)) < 128.0

    assert "Held-out Validation Task Sets" in reflection_svg
    assert "Reflection Rules on Website V3" in reflection_svg
    assert ">V1<" in reflection_svg
    assert ">V4<" in reflection_svg

    assert "# Poster Summary Figures Report" in report
    assert "../../figures/training_task_sets_main_poster_summary.svg" in report
    assert "../../figures/training_task_sets_reflection_v3_poster_summary.svg" in report
    assert "../../figures/heldout_validation_task_sets_main_poster_summary.svg" in report
    assert "../../figures/heldout_validation_task_sets_reflection_v3_poster_summary.svg" in report
    assert "4-panel poster layout" in report
    assert "ExpeL degrades under website drift" in report
