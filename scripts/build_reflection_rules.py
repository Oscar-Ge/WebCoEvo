#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.rule_pipeline.reflection_merge import (
    apply_rule_proposals,
    load_base_rulebook_payload,
)
from linkding_xvr_minimal.rule_pipeline.reflection_proposals import (
    build_openai_proposal_fn,
    build_reflection_proposal_prompt,
    build_stub_proposal_fn,
    parse_rule_proposals,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rulebook", required=True)
    parser.add_argument("--mining-cases", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--stub-proposals-file", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--candidate-version", default="generated")
    parser.add_argument("--max-rules", type=int, default=8)
    parser.add_argument("--allow-task-scope", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    base_payload = load_base_rulebook_payload(args.base_rulebook)
    cases = _load_jsonl(args.mining_cases)
    prompt = build_reflection_proposal_prompt(cases, base_payload.get("rules") or [])
    if args.stub_proposals_file:
        proposal_fn = build_stub_proposal_fn(args.stub_proposals_file)
    else:
        proposal_fn = build_openai_proposal_fn(
            base_url=args.base_url,
            api_key=args.api_key,
            model=args.model,
        )
    proposal_text = proposal_fn(prompt)
    parsed = parse_rule_proposals(proposal_text, allow_task_scope=args.allow_task_scope)
    candidate = apply_rule_proposals(
        base_payload,
        parsed["accepted"],
        version=args.candidate_version,
        max_rules=args.max_rules,
        allow_task_scope=args.allow_task_scope,
    )
    candidate["proposal_summary"] = {
        "accepted": len(parsed["accepted"]),
        "rejected": len(parsed["rejected"]),
    }
    candidate["rejected_proposals"] = parsed["rejected"]

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(candidate, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_file": str(output_path),
                "rule_count": candidate["rule_count"],
                "accepted_proposals": len(parsed["accepted"]),
                "rejected_proposals": len(parsed["rejected"]),
            },
            sort_keys=True,
        )
    )
    return 0


def _load_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
