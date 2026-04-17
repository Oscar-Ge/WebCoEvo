#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.rule_pipeline.reflection_gaps import build_behavior_gaps
from linkding_xvr_minimal.rule_pipeline.reflection_cases import build_mining_cases, write_jsonl


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--transition-artifact", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--cases-file", default="")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    transition_artifact = json.loads(Path(args.transition_artifact).read_text(encoding="utf-8"))
    gaps = build_behavior_gaps(transition_artifact)
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(gaps, indent=2), encoding="utf-8")
    if args.cases_file:
        write_jsonl(args.cases_file, build_mining_cases(transition_artifact, gaps))
    print(
        json.dumps(
            {
                "output_file": str(output_path),
                "num_gaps": gaps["summary"]["num_gaps"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
