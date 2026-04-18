import json
from pathlib import Path

from linkding_xvr_minimal.reporting_version_lines import (
    build_version_line_summary,
    render_markdown_report,
    render_version_line_svg,
)


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_build_version_line_summary_merges_hardv3_and_umich_reports(tmp_path):
    hardv3_summary = {
        "benchmarks": {
            "focus20_hardv3": {
                "label": "Focus20",
                "expected_total": 68,
                "settings": {
                    "expel_only": {"successes": 8, "overall_rate": 8 / 68},
                    "v2_4": {"successes": 65, "overall_rate": 65 / 68},
                },
            },
            "taskbank36_hardv3": {
                "label": "TaskBank36",
                "expected_total": 167,
                "settings": {
                    "expel_only": {"successes": 66, "overall_rate": 66 / 167},
                    "v2_4": {"successes": 97, "overall_rate": 97 / 167},
                },
            },
        }
    }
    umich_summary = {
        "model": "Qwen/Qwen3-VL-30B-A3B-Instruct",
        "endpoint": "http://example.test/v1",
        "scenarios": {
            "control_1450": {
                "benchmarks": {
                    "focus20": {
                        "label": "Focus20",
                        "expected_total": 68,
                        "settings": {
                            "expel_only": {
                                "successes": 56,
                                "overall_rate": 56 / 68,
                                "final_success_rate_available": True,
                                "status": "complete",
                            }
                        },
                    },
                    "taskbank36": {
                        "label": "TaskBank36",
                        "expected_total": 167,
                        "settings": {
                            "expel_only": {
                                "successes": 61,
                                "overall_rate": None,
                                "lower_bound_rate": 61 / 167,
                                "completion_rate": 98 / 167,
                                "final_success_rate_available": False,
                                "status": "partial",
                            }
                        },
                    },
                }
            },
            "first_modified": {
                "benchmarks": {
                    "focus20": {
                        "label": "Focus20",
                        "expected_total": 68,
                        "settings": {
                            "expel_only": {
                                "successes": 60,
                                "overall_rate": 60 / 68,
                                "final_success_rate_available": True,
                                "status": "complete",
                            },
                            "v2_4": {
                                "successes": 67,
                                "overall_rate": 67 / 68,
                                "final_success_rate_available": True,
                                "status": "complete",
                            },
                        },
                    },
                    "taskbank36": {
                        "label": "TaskBank36",
                        "expected_total": 167,
                        "settings": {
                            "expel_only": {
                                "successes": 114,
                                "overall_rate": 114 / 167,
                                "final_success_rate_available": True,
                                "status": "complete",
                            },
                            "v2_4": {
                                "successes": 143,
                                "overall_rate": 143 / 167,
                                "final_success_rate_available": True,
                                "status": "complete",
                            },
                        },
                    },
                }
            },
        },
    }

    hardv3_path = _write_json(tmp_path / "hardv3-summary.json", hardv3_summary)
    umich_path = _write_json(tmp_path / "umich-summary.json", umich_summary)

    summary = build_version_line_summary(hardv3_path, umich_path)

    focus20 = summary["benchmarks"]["focus20"]
    assert focus20["x_labels"] == ["Control 1.45.0", "First-Modified", "Hardv3"]
    assert focus20["series"]["expel_only"]["points"][0]["successes"] == 56
    assert focus20["series"]["expel_only"]["points"][1]["successes"] == 60
    assert focus20["series"]["v2_4"]["points"][0]["available"] is False
    assert focus20["series"]["v2_4"]["points"][1]["successes"] == 67
    assert focus20["series"]["expel_only"]["points"][2]["successes"] == 8

    taskbank36 = summary["benchmarks"]["taskbank36"]
    assert taskbank36["series"]["expel_only"]["points"][0]["available"] is False
    assert taskbank36["series"]["expel_only"]["points"][0]["status"] == "partial"
    assert taskbank36["series"]["v2_4"]["points"][1]["successes"] == 143
    assert taskbank36["series"]["v2_4"]["points"][2]["successes"] == 97


def test_renderers_include_versions_missing_points_and_report_text(tmp_path):
    summary = {
        "model": "Qwen/Qwen3-VL-30B-A3B-Instruct",
        "endpoint": "http://example.test/v1",
        "benchmarks": {
            "focus20": {
                "label": "Focus20",
                "x_labels": ["Control 1.45.0", "First-Modified", "Hardv3"],
                "series_order": ["expel_only", "v2_4"],
                "series": {
                    "expel_only": {
                        "label": "ExpeL Only",
                        "points": [
                            {"available": True, "successes": 56, "total": 68, "rate": 56 / 68},
                            {"available": True, "successes": 60, "total": 68, "rate": 60 / 68},
                            {"available": True, "successes": 8, "total": 68, "rate": 8 / 68},
                        ],
                    },
                    "v2_4": {
                        "label": "V2.4",
                        "points": [
                            {"available": False, "status": "missing"},
                            {"available": True, "successes": 67, "total": 68, "rate": 67 / 68},
                            {"available": True, "successes": 65, "total": 68, "rate": 65 / 68},
                        ],
                    },
                },
            },
            "taskbank36": {
                "label": "TaskBank36",
                "x_labels": ["Control 1.45.0", "First-Modified", "Hardv3"],
                "series_order": ["expel_only", "v2_4"],
                "series": {
                    "expel_only": {
                        "label": "ExpeL Only",
                        "points": [
                            {"available": False, "status": "partial"},
                            {"available": True, "successes": 114, "total": 167, "rate": 114 / 167},
                            {"available": True, "successes": 66, "total": 167, "rate": 66 / 167},
                        ],
                    },
                    "v2_4": {
                        "label": "V2.4",
                        "points": [
                            {"available": False, "status": "missing"},
                            {"available": True, "successes": 143, "total": 167, "rate": 143 / 167},
                            {"available": True, "successes": 97, "total": 167, "rate": 97 / 167},
                        ],
                    },
                },
            },
        },
    }

    svg = render_version_line_svg("focus20", summary["benchmarks"]["focus20"])
    report = render_markdown_report(
        summary,
        figure_paths={
            "focus20": "../../figures/focus20_version_lines.svg",
            "taskbank36": "../../figures/taskbank36_version_lines.svg",
        },
    )

    assert "Control 1.45.0" in svg
    assert "First-Modified" in svg
    assert "Hardv3" in svg
    assert "N/A" in svg

    assert "# Website Version Line Report" in report
    assert "../../figures/focus20_version_lines.svg" in report
    assert "Control 1.45.0" in report
    assert "First-Modified" in report
    assert "TaskBank36 control point is unavailable" in report
