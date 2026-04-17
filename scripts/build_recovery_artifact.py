#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.rule_pipeline.recovery import build_recovery_artifact


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes-file", required=True)
    parser.add_argument("--output-file", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    payload = json.loads(Path(args.episodes_file).read_text(encoding="utf-8"))
    episodes = list(payload.get("episodes", []) or [])
    recovery = build_recovery_artifact(episodes)
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(recovery, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_file": str(output_path),
                "num_tasks": recovery["summary"]["num_tasks"],
                "num_failed_then_success_tasks": recovery["summary"]["num_failed_then_success_tasks"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
