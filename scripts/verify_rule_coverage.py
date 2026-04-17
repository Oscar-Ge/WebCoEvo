#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.browser_task import compile_raw_task
from linkding_xvr_minimal.expel_rules import load_expel_rules
from linkding_xvr_minimal.rule_pipeline.coverage import build_pipeline_report
from linkding_xvr_minimal.rulebook import load_rulebook
from linkding_xvr_minimal.tasks import load_raw_tasks


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--rulebook", required=True)
    parser.add_argument("--expel-rule-file", default="")
    parser.add_argument("--rule-limit", type=int, default=8)
    parser.add_argument("--expel-rule-limit", type=int, default=3)
    parser.add_argument("--expel-fidelity", default="minimal")
    parser.add_argument("--require-full-xvr-coverage", action="store_true", default=False)
    parser.add_argument("--require-full-expel-coverage", action="store_true", default=False)
    parser.add_argument("--json", action="store_true", default=False)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    rows = load_raw_tasks(Path(args.task_file))
    specs = [compile_raw_task(row) for row in rows]
    rulebook = load_rulebook(Path(args.rulebook))
    expel_rulebook = load_expel_rules(Path(args.expel_rule_file)) if args.expel_rule_file else None

    report = build_pipeline_report(
        specs=specs,
        rulebook=rulebook,
        expel_rulebook=expel_rulebook,
        limit=args.rule_limit,
        expel_limit=args.expel_rule_limit,
        expel_fidelity=args.expel_fidelity,
        fail_on_empty=args.require_full_xvr_coverage,
    )

    if args.require_full_xvr_coverage and report["xvr"]["missing_task_ids"]:
        print("missing xvr coverage for task_ids {}".format(report["xvr"]["missing_task_ids"]), file=sys.stderr)
        return 2
    if args.require_full_expel_coverage and report["expel"]["missing_task_ids"]:
        print("missing expel coverage for task_ids {}".format(report["expel"]["missing_task_ids"]), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "task_count={task_count} xvr_covered={xvr[covered]} expel_covered={expel[covered]}".format(
                **report
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
