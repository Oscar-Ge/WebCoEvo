#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.rule_pipeline.reflection_compare import (
    build_transition_artifact,
    load_jsonl,
)
from linkding_xvr_minimal.tasks import load_raw_tasks


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--left-label", required=True)
    parser.add_argument("--left-eval", required=True)
    parser.add_argument("--left-trace", required=True)
    parser.add_argument("--right-label", required=True)
    parser.add_argument("--right-eval", required=True)
    parser.add_argument("--right-trace", required=True)
    parser.add_argument("--output-file", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    task_rows = load_raw_tasks(Path(args.task_file))
    payload = build_transition_artifact(
        task_rows=task_rows,
        left_eval_rows=load_jsonl(args.left_eval),
        left_trace_rows=load_jsonl(args.left_trace),
        right_eval_rows=load_jsonl(args.right_eval),
        right_trace_rows=load_jsonl(args.right_trace),
        left_label=args.left_label,
        right_label=args.right_label,
        task_file=args.task_file,
    )
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_file": str(output_path),
                "num_rows": payload["summary"]["num_rows"],
                "transition_counts": payload["summary"]["transition_counts"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
