#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.rule_pipeline.reflection_verify import build_verification_report


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--rulebook", required=True)
    parser.add_argument("--max-rules", type=int, default=8)
    parser.add_argument("--rule-limit", type=int, default=8)
    parser.add_argument("--no-task-scopes", action="store_true", default=False)
    parser.add_argument("--require-full-coverage", action="store_true", default=False)
    parser.add_argument("--required-gap-phrase", action="append", default=[])
    parser.add_argument("--json", action="store_true", default=False)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    payload = json.loads(Path(args.rulebook).read_text(encoding="utf-8"))
    report = build_verification_report(
        payload,
        task_file=args.task_file,
        rulebook_path=args.rulebook,
        max_rules=args.max_rules,
        no_task_scopes=args.no_task_scopes,
        required_gap_phrases=args.required_gap_phrase,
        rule_limit=args.rule_limit,
    )
    if not args.require_full_coverage and report.get("coverage"):
        report["ok"] = bool(report["contract"]["ok"])
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "ok={ok} rule_count={contract[rule_count]} covered={coverage_covered}".format(
                ok=report["ok"],
                contract=report["contract"],
                coverage_covered=(report.get("coverage") or {}).get("covered", 0),
            )
        )
    if not report["contract"]["ok"]:
        return 2
    if args.require_full_coverage and (report.get("coverage") or {}).get("missing_task_ids"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
