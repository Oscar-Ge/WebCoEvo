#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.rule_pipeline.reflection_cases import build_mining_cases, write_jsonl
from linkding_xvr_minimal.rule_pipeline.reflection_compare import build_transition_artifact, load_jsonl
from linkding_xvr_minimal.rule_pipeline.reflection_delta import (
    build_delta_manifest,
    build_delta_task_file,
    select_delta_rows,
)
from linkding_xvr_minimal.rule_pipeline.reflection_gaps import build_behavior_gaps
from linkding_xvr_minimal.tasks import load_raw_tasks


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-file", required=True)
    parser.add_argument("--focus20-task-file", required=True)
    parser.add_argument("--taskbank-task-file", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    manifest = json.loads(Path(args.manifest_file).read_text(encoding="utf-8"))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    focus20_summary = build_casebook_bundle(
        dataset_name="focus20",
        left_entry=manifest["focus20"]["first_modified"]["v2_4"],
        right_entry=manifest["focus20"]["hardv3"]["v2_4"],
        task_file=args.focus20_task_file,
        output_dir=output_dir,
        include_gap_outputs=True,
    )
    taskbank_summary = build_casebook_bundle(
        dataset_name="taskbank36",
        left_entry=manifest["taskbank36"]["first_modified"]["v2_4"],
        right_entry=manifest["taskbank36"]["hardv3"]["v2_4"],
        task_file=args.taskbank_task_file,
        output_dir=output_dir,
        include_gap_outputs=False,
    )

    print(
        json.dumps(
            {
                "focus20": focus20_summary,
                "taskbank36": taskbank_summary,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def build_casebook_bundle(dataset_name, left_entry, right_entry, task_file, output_dir, include_gap_outputs):
    task_rows = load_raw_tasks(Path(task_file))
    transition = build_transition_artifact(
        task_rows=task_rows,
        left_eval_rows=load_manifest_rows(left_entry, "eval"),
        left_trace_rows=load_manifest_rows(left_entry, "trace"),
        right_eval_rows=load_manifest_rows(right_entry, "eval"),
        right_trace_rows=load_manifest_rows(right_entry, "trace"),
        left_label="first_modified_v2_4",
        right_label="hardv3_v2_4",
        task_file=task_file,
        provenance={
            "task_file": task_file,
            "left_run_dir": left_entry.get("run_dir", ""),
            "right_run_dir": right_entry.get("run_dir", ""),
        },
    )

    transition_path = output_dir / "{}_transition_first_modified_to_hardv3.json".format(dataset_name)
    transition_path.write_text(json.dumps(transition, indent=2, sort_keys=True), encoding="utf-8")

    gap_payload = None
    mining_cases = []
    if include_gap_outputs:
        gap_payload = build_behavior_gaps(transition)
        gap_path = output_dir / "{}_behavior_gaps.json".format(dataset_name)
        gap_path.write_text(json.dumps(gap_payload, indent=2, sort_keys=True), encoding="utf-8")

        mining_cases = build_mining_cases(transition, gap_payload)
        write_jsonl(output_dir / "{}_mining_cases.jsonl".format(dataset_name), mining_cases)

        selection = select_delta_rows(transition, max_per_bucket=8)
        delta_rows = build_delta_task_file(task_rows, selection["selected_task_ids"])
        delta_task_path = output_dir / "{}_delta_tasks.json".format(dataset_name)
        delta_task_path.write_text(json.dumps(delta_rows, indent=2, sort_keys=True), encoding="utf-8")
        delta_manifest = build_delta_manifest(
            selection,
            output_task_file=str(delta_task_path),
            max_per_bucket=8,
        )
        delta_manifest_path = output_dir / "{}_delta_manifest.json".format(dataset_name)
        delta_manifest_path.write_text(
            json.dumps(delta_manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    casebook_path = output_dir / "{}_casebook.md".format(dataset_name)
    casebook_path.write_text(
        render_casebook_markdown(
            dataset_name=dataset_name,
            transition_artifact=transition,
            gap_payload=gap_payload,
            mining_cases=mining_cases,
        ),
        encoding="utf-8",
    )

    return {
        "transition_counts": transition["summary"]["transition_counts"],
        "num_rows": transition["summary"]["num_rows"],
    }


def load_manifest_rows(entry, row_type):
    key = "{}_paths".format(row_type)
    fallback_key = "{}_path".format(row_type)
    rows = []
    paths = list(entry.get(key) or [])
    if not paths and entry.get(fallback_key):
        paths = [entry[fallback_key]]
    for path in paths:
        rows.extend(load_jsonl(path))
    return rows


def render_casebook_markdown(dataset_name, transition_artifact, gap_payload, mining_cases):
    summary = dict((transition_artifact or {}).get("summary") or {})
    counts = dict(summary.get("transition_counts") or {})
    both_success_rows = select_rows_by_transition(transition_artifact, "both_success")
    lost_rows = select_rows_by_transition(transition_artifact, "lost")
    lines = [
        "# {} Casebook".format(dataset_name),
        "",
        "## Transition Legend",
        "- `both_success`: old success -> new success",
        "- `lost`: old success -> new fail",
        "- `saved`: old fail -> new success",
        "- `both_fail`: old fail -> new fail",
        "",
        "## Transition Counts",
    ]
    for key in sorted(counts):
        lines.append("- `{}`: {}".format(key, counts[key]))

    if gap_payload:
        lines.extend(["", "## Top Behavior Gaps"])
        for gap in list(gap_payload.get("gaps") or [])[:5]:
            lines.append(
                "- `{}`: {} (task_ids: {})".format(
                    gap.get("gap_id", ""),
                    gap.get("label", ""),
                    ",".join(str(task_id) for task_id in list(gap.get("supporting_task_ids") or [])),
                )
            )

    if mining_cases:
        lines.extend(["", "## Mining Cases"])
        for case in list(mining_cases or [])[:5]:
            lines.append(
                "- `{}` -> `{}`".format(
                    case.get("case_id", ""),
                    ((case.get("diagnosis") or {}).get("observed_gap") or ""),
                )
            )

    lines.extend(["", "## Representative `both_success` Excerpts"])
    lines.extend(render_row_examples(both_success_rows))
    lines.extend(["", "## Representative `lost` Excerpts"])
    lines.extend(render_row_examples(lost_rows))
    return "\n".join(lines).strip() + "\n"


def render_row_examples(rows):
    if not rows:
        return ["- none"]
    rendered = []
    for row in list(rows or [])[:3]:
        rendered.append(
            "- task {} (`{}` / `{}`)".format(
                row.get("task_id", ""),
                row.get("drift_type", ""),
                row.get("transition", ""),
            )
        )
        rendered.append(
            "  left: {}".format(compact_trace_excerpt(row.get("left_trace_excerpt") or []))
        )
        rendered.append(
            "  right: {}".format(compact_trace_excerpt(row.get("right_trace_excerpt") or []))
        )
    return rendered


def compact_trace_excerpt(rows):
    parts = []
    for row in list(rows or [])[:2]:
        parts.append(
            "step {} action={} url={} error={} final={}".format(
                row.get("step", ""),
                str(row.get("action") or "").strip() or "-",
                str(row.get("url") or "").strip() or "-",
                str(row.get("error") or "").strip() or "-",
                str(row.get("final_answer") or "").strip() or "-",
            )
        )
    return " | ".join(parts) if parts else "no trace excerpt"


def select_rows_by_transition(transition_artifact, transition_name):
    return [
        row
        for row in list((transition_artifact or {}).get("rows") or [])
        if str(row.get("transition") or "") == transition_name
    ]


if __name__ == "__main__":
    raise SystemExit(main())
