#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.rule_pipeline.reflection_delta import (
    build_delta_manifest,
    build_delta_task_file,
    select_delta_rows,
)
from linkding_xvr_minimal.tasks import load_raw_tasks


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--transition-artifact", required=True)
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--output-task-file", required=True)
    parser.add_argument("--manifest-file", required=True)
    parser.add_argument("--max-per-bucket", type=int, default=8)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    transition_artifact = json.loads(Path(args.transition_artifact).read_text(encoding="utf-8"))
    task_rows = load_raw_tasks(Path(args.task_file))
    selection = select_delta_rows(transition_artifact, max_per_bucket=args.max_per_bucket)
    delta_rows = build_delta_task_file(task_rows, selection["selected_task_ids"])
    manifest = build_delta_manifest(
        selection,
        output_task_file=args.output_task_file,
        max_per_bucket=args.max_per_bucket,
    )

    output_path = Path(args.output_task_file)
    manifest_path = Path(args.manifest_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(delta_rows, indent=2, sort_keys=True), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_task_file": str(output_path),
                "manifest_file": str(manifest_path),
                "selected_count": len(delta_rows),
                "bucket_counts": manifest["bucket_counts"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
