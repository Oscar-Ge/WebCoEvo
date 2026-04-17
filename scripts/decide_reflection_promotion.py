#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.rule_pipeline.reflection_decision import (
    decide_promotion,
    render_promotion_decision_md,
    summarize_transition_artifact,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--transition-artifact", required=True)
    parser.add_argument("--verification-report", default="")
    parser.add_argument("--focus20-report", default="")
    parser.add_argument("--heldout-report", default="")
    parser.add_argument("--output-file", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    transition_artifact = _load_json(args.transition_artifact)
    verification_report = _load_json(args.verification_report) if args.verification_report else None
    focus20_report = _load_json(args.focus20_report) if args.focus20_report else None
    heldout_report = _load_json(args.heldout_report) if args.heldout_report else None

    summary = summarize_transition_artifact(transition_artifact)
    decision = decide_promotion(
        summary,
        focus20_report=focus20_report,
        heldout_report=heldout_report,
        verification_report=verification_report,
    )
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_promotion_decision_md(decision), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_file": str(output_path),
                "decision": decision["decision"],
                "reasons": decision["reasons"],
            },
            sort_keys=True,
        )
    )
    return 0


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
