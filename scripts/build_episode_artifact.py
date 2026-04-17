#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.rule_pipeline.episodes import collect_episodes


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True)
    parser.add_argument("--eval", required=True)
    parser.add_argument("--task-file", default="")
    parser.add_argument("--source-version", default="")
    parser.add_argument("--experience-fidelity", default="alpha")
    parser.add_argument("--output-file", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    episodes = collect_episodes(
        trace_path=args.trace,
        eval_path=args.eval,
        task_file=args.task_file or None,
        source_version=args.source_version,
        experience_fidelity=args.experience_fidelity,
    )
    payload = {
        "schema_version": "webcoevo-rule-episodes-v1",
        "summary": {
            "num_episodes": len(episodes),
            "source_version": args.source_version,
            "experience_fidelity": args.experience_fidelity,
        },
        "episodes": episodes,
    }
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_file": str(output_path),
                "num_episodes": len(episodes),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
