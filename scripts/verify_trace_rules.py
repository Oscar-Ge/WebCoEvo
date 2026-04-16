#!/usr/bin/env python3
import argparse
import glob
import json
import sys


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True, nargs="+")
    parser.add_argument("--require-cross-version-rules", action="store_true", default=False)
    parser.add_argument("--require-rulebook-path", action="store_true", default=False)
    parser.add_argument("--require-expel-rules", action="store_true", default=False)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    paths = []
    for pattern in args.trace:
        matches = sorted(glob.glob(pattern))
        paths.extend(matches or [pattern])
    rows = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        row = json.loads(line)
                        row["_path"] = path
                        rows.append(row)
        except OSError as exc:
            print("failed to read trace {}: {}".format(path, exc), file=sys.stderr)
            return 2
    if not rows:
        print("no trace rows found", file=sys.stderr)
        return 2

    errors = []
    task_seen = {}
    for row in rows:
        task_id = row.get("task_id", "<unknown>")
        if task_id not in task_seen:
            task_seen[task_id] = row
    for task_id, row in sorted(task_seen.items(), key=lambda item: str(item[0])):
        if args.require_cross_version_rules and not row.get("cross_version_reflection_rule_ids"):
            errors.append("task {} missing cross_version_reflection_rule_ids".format(task_id))
        if args.require_rulebook_path and not row.get("cross_version_reflection_rules_path"):
            errors.append("task {} missing cross_version_reflection_rules_path".format(task_id))
        if args.require_expel_rules and not row.get("injected_rule_ids"):
            errors.append("task {} missing injected_rule_ids".format(task_id))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "trace_files": paths,
                "rows": len(rows),
                "tasks": len(task_seen),
                "ok": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
