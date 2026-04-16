import argparse
import json
import os
import sys
from pathlib import Path

from linkding_xvr_minimal.agent import build_cross_version_prompt_payload
from linkding_xvr_minimal.browser_task import compile_raw_task
from linkding_xvr_minimal.expel_rules import build_expel_prompt_payload, load_expel_rules
from linkding_xvr_minimal.rulebook import load_rulebook
from linkding_xvr_minimal.tasks import filter_tasks, load_raw_tasks, normalize_task_metadata


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Minimal Linkding XVR runner")
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--rulebook", required=True)
    parser.add_argument("--run-label", required=True)
    parser.add_argument("--variant", default="")
    parser.add_argument("--drift-type", default="")
    parser.add_argument("--task-id", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--model", default=os.getenv("UITARS_MODEL", "Qwen/Qwen3-VL-30B-A3B-Instruct"))
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL", ""))
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY", ""))
    parser.add_argument("--agent-mode", choices=("text_only", "vl_action_reflection"), default="text_only")
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--compile-only", action="store_true", default=False)
    parser.add_argument("--preflight-rules-only", action="store_true", default=False)
    parser.add_argument("--fail-on-empty-xvr-rules", action="store_true", default=False)
    parser.add_argument("--study-dir", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--rule-limit", type=int, default=8)
    parser.add_argument("--expel-rule-file", default="")
    parser.add_argument("--expel-rule-limit", type=int, default=3)
    parser.add_argument(
        "--expel-fidelity",
        choices=("minimal", "official_eval", "official_full"),
        default="minimal",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        rows = load_raw_tasks(Path(args.task_file))
        rows = filter_tasks(
            rows,
            task_id=args.task_id,
            limit=args.limit,
            variant=args.variant,
            drift_type=args.drift_type,
        )
        specs = [compile_raw_task(row) for row in rows]
        rulebook = load_rulebook(Path(args.rulebook))
        expel_rulebook = load_expel_rules(Path(args.expel_rule_file)) if args.expel_rule_file else None
        if args.compile_only:
            _print_json(compile_summary(specs))
            return 0
        preflight = preflight_rule_selection(
            specs,
            rulebook,
            limit=args.rule_limit,
            fail_on_empty=args.fail_on_empty_xvr_rules,
        )
        expel_preflight = preflight_expel_rule_selection(
            specs,
            expel_rulebook,
            limit=args.expel_rule_limit,
            fidelity=args.expel_fidelity,
        )
        if args.preflight_rules_only:
            _print_json(
                {
                    "task_count": len(specs),
                    "preflight": preflight,
                    "expel_preflight": expel_preflight,
                }
            )
            return 0
        return run_agentlab(args, specs, rulebook, preflight, expel_preflight)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


def compile_summary(specs):
    tasks = []
    for spec in specs:
        metadata = (spec.metadata or {}).get("normalized_task") or {}
        row = dict(metadata)
        row.update(
            {
                "task_name": spec.task_name,
                "site": spec.site,
                "require_login": spec.require_login,
                "require_reset": spec.require_reset,
            }
        )
        tasks.append(row)
    return {"task_count": len(specs), "tasks": tasks}


def preflight_rule_selection(specs, rulebook, limit=8, fail_on_empty=False):
    rows = []
    for spec in specs:
        metadata = (spec.metadata or {}).get("normalized_task") or {}
        payload = build_cross_version_prompt_payload(
            rulebook=rulebook,
            task_metadata=metadata,
            limit=limit,
            fail_on_empty=fail_on_empty,
        )
        selection = payload["selection"]
        rows.append(
            {
                "task_id": spec.task_id,
                "task_name": spec.task_name,
                "selected_rule_ids": selection["selected_rule_ids"],
                "rulebook_path": selection["rulebook_path"],
                "selection_context": selection["selection_context"],
                "miss_reasons": selection["miss_reasons"],
                "warning": selection["warning"],
            }
        )
    return rows


def preflight_expel_rule_selection(specs, expel_rulebook, limit=3, fidelity="minimal"):
    if not expel_rulebook:
        return []
    rows = []
    for spec in specs:
        metadata = (spec.metadata or {}).get("normalized_task") or {}
        payload = build_expel_prompt_payload(
            rulebook=expel_rulebook,
            task_metadata=metadata,
            limit=limit,
            fidelity=fidelity,
        )
        selection = payload["selection"]
        rows.append(
            {
                "task_id": spec.task_id,
                "task_name": spec.task_name,
                "selected_rule_ids": selection["selected_rule_ids"],
                "rulebook_path": selection["rulebook_path"],
                "selection_context": selection["selection_context"],
                "fidelity": selection["fidelity"],
            }
        )
    return rows


def build_task_context_json(specs):
    contexts = []
    for spec in specs:
        metadata = dict((spec.metadata or {}).get("normalized_task") or {})
        metadata["goal"] = spec.intent
        contexts.append(
            {
                "task_name": spec.task_name,
                "goal": spec.intent,
                "goal_prefixed": "Goal: {}".format(spec.intent),
                "start_url": spec.start_url,
                "metadata": metadata,
            }
        )
    return json.dumps(contexts, ensure_ascii=False, sort_keys=True)


def run_agentlab(args, specs, rulebook, preflight, expel_preflight=None):
    try:
        from agentlab.experiments.study import Study
        from linkding_xvr_minimal.agentlab_agent import UITARSAgentLabArgs
        from linkding_xvr_minimal.benchmark import build_benchmark
        from linkding_xvr_minimal.export import export_agentlab_study_to_legacy_jsonl
    except Exception as exc:
        raise RuntimeError("AgentLab runtime dependencies are unavailable: {}".format(exc))

    if not args.base_url:
        raise RuntimeError("Missing --base-url / OPENAI_BASE_URL")
    if not args.api_key:
        raise RuntimeError("Missing --api-key / OPENAI_API_KEY")

    output_dir = Path(args.output_dir) if args.output_dir else Path("results") / args.run_label
    study_dir = Path(args.study_dir) if args.study_dir else output_dir / "study"
    benchmark = build_benchmark(
        specs,
        benchmark_name=args.run_label,
        max_steps=args.max_steps,
        headless=args.headless,
    )
    study = Study(
        benchmark=benchmark,
        agent_args=[
            UITARSAgentLabArgs(
                model=args.model,
                base_url=args.base_url,
                api_key=args.api_key,
                max_tokens=args.max_tokens,
                agent_mode=args.agent_mode,
                rulebook_path=str(args.rulebook),
                expel_rule_file=str(args.expel_rule_file or ""),
                expel_fidelity=args.expel_fidelity,
                task_context_json=build_task_context_json(specs),
                rule_limit=args.rule_limit,
                expel_rule_limit=args.expel_rule_limit,
                fail_on_empty_xvr_rules=args.fail_on_empty_xvr_rules,
            )
        ],
        comment="Minimal Linkding XVR run",
    )
    study.dir = study_dir
    study.run(n_jobs=1, parallel_backend="sequential")
    exported = export_agentlab_study_to_legacy_jsonl(
        study_dir=study.dir,
        specs=specs,
        output_dir=output_dir,
        stem="uitars",
        preflight=preflight,
        expel_preflight=expel_preflight or [],
    )
    _print_json(
        {
            "study_dir": str(study.dir),
            "legacy_eval_jsonl": str(exported["eval_path"]),
            "legacy_trace_jsonl": str(exported["trace_path"]),
            "task_count": len(specs),
            "preflight": preflight,
            "expel_preflight": expel_preflight or [],
        }
    )
    return 0


def _print_json(payload):
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
