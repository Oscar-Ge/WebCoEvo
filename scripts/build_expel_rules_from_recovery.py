#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.rule_pipeline.induction import (
    extract_insight_rows,
    mine_specific_rules_from_cases,
)
from linkding_xvr_minimal.rule_pipeline.recovery import (
    extract_failed_then_success_cases,
    flatten_failed_then_success_episodes,
)


def _extract_json_array(text):
    stripped = str(text or "").strip()
    if not stripped:
        return []
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped).strip()
    start = stripped.find("[")
    end = stripped.rfind("]")
    if start >= 0 and end > start:
        stripped = stripped[start : end + 1]
    return json.loads(stripped)


def build_stub_reflect_fn(stub_path):
    rows = json.loads(Path(stub_path).read_text(encoding="utf-8"))

    def _reflect(_prompt):
        return list(rows)

    return _reflect


def build_stub_critique_fn(stub_path):
    response = Path(stub_path).read_text(encoding="utf-8")

    def _critique(_prompt):
        return response

    return _critique


def build_openai_reflect_fn(base_url, api_key, model):
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=api_key)

    def _reflect(prompt):
        response = client.chat.completions.create(
            model=model,
            temperature=0.0,
            max_tokens=700,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You summarize web-agent failure-to-success trajectories in ExpeL style. "
                        "Return only a JSON array. "
                        "Each element must contain: summary, when, query_terms."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        return _extract_json_array(str(response.choices[0].message.content or "[]"))

    return _reflect


def build_openai_critique_fn(base_url, api_key, model):
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=api_key)

    def _critique(prompt):
        response = client.chat.completions.create(
            model=model,
            temperature=0.0,
            max_tokens=700,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an ExpeL-style rule induction module for a web agent. "
                        "Return only rule operations using these exact formats: "
                        "ADD: ..., AGREE <n>: ..., EDIT <n>: ..., REMOVE <n>: .... "
                        "Every rule must end with a period."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        return str(response.choices[0].message.content or "").strip()

    return _critique


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery-artifact", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL", ""))
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY", ""))
    parser.add_argument("--model", default=os.getenv("UITARS_MODEL", "") or "gpt-5.4")
    parser.add_argument("--max-num-rules", type=int, default=20)
    parser.add_argument("--success-critique-num", type=int, default=1)
    parser.add_argument("--min-rules", type=int, default=1)
    parser.add_argument("--include-insights", action="store_true", default=False)
    parser.add_argument("--stub-critique-file", default="")
    parser.add_argument("--stub-insights-file", default="")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    recovery_artifact_path = Path(args.recovery_artifact)
    payload = json.loads(recovery_artifact_path.read_text(encoding="utf-8"))
    cases = extract_failed_then_success_cases(payload)
    episodes = flatten_failed_then_success_episodes(cases)

    if args.stub_critique_file:
        critique_fn = build_stub_critique_fn(args.stub_critique_file)
    else:
        if not args.base_url or not args.api_key:
            raise SystemExit("OPENAI_BASE_URL / --base-url and OPENAI_API_KEY / --api-key are required")
        critique_fn = build_openai_critique_fn(args.base_url, args.api_key, args.model)

    if args.include_insights:
        if args.stub_insights_file:
            reflect_fn = build_stub_reflect_fn(args.stub_insights_file)
        else:
            if not args.base_url or not args.api_key:
                raise SystemExit("OPENAI_BASE_URL / --base-url and OPENAI_API_KEY / --api-key are required")
            reflect_fn = build_openai_reflect_fn(args.base_url, args.api_key, args.model)
        insights = extract_insight_rows(episodes, reflect_fn=reflect_fn)
    else:
        insights = []

    rules, generation_records = mine_specific_rules_from_cases(
        cases,
        critique_fn=critique_fn,
        max_num_rules=args.max_num_rules,
        success_critique_num=args.success_critique_num,
    )

    if len(rules) < int(args.min_rules):
        raise SystemExit("expected at least {} rules, got {}".format(int(args.min_rules), len(rules)))

    success_insights = [row for row in insights if row.get("outcome_tag") == "success"]
    failure_insights = [row for row in insights if row.get("outcome_tag") == "failure"]
    out_payload = {
        "schema_version": "webcoevo-expel-memory-v1",
        "summary": {
            "num_episodes": len(episodes),
            "num_failed_then_success_tasks": len(cases),
            "num_rules": len(rules),
            "num_insights": len(insights),
            "num_success_insights": len(success_insights),
            "num_failure_insights": len(failure_insights),
            "num_retrieval_episodes": 0,
            "rule_mining_mode": "failed_then_success_specific_v1",
            "source_recovery_artifact": str(recovery_artifact_path),
            "extraction_model": args.model,
            "target_max_num_rules": int(args.max_num_rules),
        },
        "episodes": episodes,
        "rules": rules,
        "insights": insights,
        "success_insights": success_insights,
        "failure_insights": failure_insights,
        "retrieval_episodes": [],
        "source_cases": [
            {
                "task_id": int(case.get("task_id", 0)),
                "goal": str(case.get("goal", "")),
                "version": str(case.get("version", "")),
                "failure_attempt_count": int(case.get("failure_attempt_count", 0)),
                "success_attempt_index": int(case.get("success_attempt_index", 0) or 0),
            }
            for case in cases
        ],
        "rule_generation_records": generation_records,
    }

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_file": str(output_path),
                "num_cases": len(cases),
                "num_episodes": len(episodes),
                "num_rules": len(rules),
                "num_insights": len(insights),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
