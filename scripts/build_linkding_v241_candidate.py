#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.rule_pipeline.reflection_cases import build_diagnosis, build_mining_case
from linkding_xvr_minimal.rule_pipeline.reflection_merge import (
    apply_rule_proposals,
    load_base_rulebook_payload,
)
from linkding_xvr_minimal.rule_pipeline.reflection_proposals import (
    extract_json_payload,
    parse_rule_proposals,
    request_openai_compatible_text,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--env-file", default="")
    parser.add_argument("--base-rulebook", required=True)
    parser.add_argument("--manifest-file", required=True)
    parser.add_argument("--casebook-file", required=True)
    parser.add_argument("--mining-cases", required=True)
    parser.add_argument("--output-rulebook", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--candidate-version", default="v2_4_1")
    parser.add_argument("--max-rules", type=int, default=8)
    parser.add_argument("--allow-task-scope", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    config = resolve_provider_config(
        base_url=args.base_url,
        api_key=args.api_key,
        model=args.model,
        env_file=args.env_file,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    api_smoke = load_json(output_dir / "api_smoke.json")
    if not (api_smoke.get("chat_ok") or api_smoke.get("ok") or api_smoke.get("generation_ok")):
        raise SystemExit("api_smoke.json does not confirm a usable generation endpoint")

    manifest = load_json(args.manifest_file)
    base_payload = load_base_rulebook_payload(args.base_rulebook)
    casebook_text = Path(args.casebook_file).read_text(encoding="utf-8")
    transition_artifact = load_json(output_dir / "focus20_transition_first_modified_to_hardv3.json")
    mining_cases = load_jsonl(args.mining_cases)
    evidence = build_evidence_bundle(
        mining_cases=mining_cases,
        transition_artifact=transition_artifact,
        casebook_text=casebook_text,
    )

    prompt = build_candidate_prompt(
        base_rules=base_payload.get("rules") or [],
        manifest=manifest,
        evidence=evidence,
    )
    generation = request_openai_compatible_text(
        prompt=prompt,
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        system_prompt=(
            "Return only JSON with a summary object and a proposals array for cross-version "
            "reflection rulebook edits."
        ),
    )
    parsed = parse_rule_proposals(
        generation["text"],
        allow_task_scope=args.allow_task_scope,
    )
    provider_payload = extract_json_payload(generation["text"])
    provider_summary = _as_dict(provider_payload.get("summary") if isinstance(provider_payload, dict) else {})
    required_gap_phrases = unique_phrases(
        list(evidence.get("required_gap_phrases") or [])
        + list(provider_summary.get("required_gap_phrases") or [])
    )

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
    candidate["required_gap_phrases"] = required_gap_phrases
    candidate["generation_endpoint"] = generation["selected_transport"]

    output_rulebook = Path(args.output_rulebook)
    output_rulebook.parent.mkdir(parents=True, exist_ok=True)
    output_rulebook.write_text(json.dumps(candidate, indent=2, sort_keys=True), encoding="utf-8")

    raw_output = {
        "schema_version": "webcoevo-linkding-v241-provider-output-v1",
        "base_url": config["base_url"],
        "model": config["model"],
        "selected_transport": generation["selected_transport"],
        "selected_endpoint": generation["selected_endpoint"],
        "response_text": generation["text"],
        "selected_response_body": generation["selected_response_body"],
        "attempts": generation["attempts"],
        "prompt": prompt,
    }
    (output_dir / "gpt54_proposals_raw.json").write_text(
        json.dumps(raw_output, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    summary_payload = {
        "schema_version": "webcoevo-linkding-v241-candidate-summary-v1",
        "candidate_version": args.candidate_version,
        "selected_transport": generation["selected_transport"],
        "proposal_summary": {
            "accepted": len(parsed["accepted"]),
            "rejected": len(parsed["rejected"]),
        },
        "provider_summary": {
            "preserve_patterns": list(provider_summary.get("preserve_patterns") or []),
            "lost_patterns": list(provider_summary.get("lost_patterns") or []),
        },
        "required_gap_phrases": required_gap_phrases,
        "evidence": evidence,
        "output_rulebook": str(output_rulebook),
    }
    (output_dir / "gpt54_candidate_summary.json").write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "output_rulebook": str(output_rulebook),
                "rule_count": candidate["rule_count"],
                "selected_transport": generation["selected_transport"],
                "evidence_mode": evidence["mode"],
            },
            sort_keys=True,
        )
    )
    return 0


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path):
    rows = []
    input_path = Path(path)
    if not input_path.exists():
        return rows
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def load_env_file(path):
    env = {}
    if not path:
        return env
    env_path = Path(path)
    if not env_path.exists():
        raise FileNotFoundError("env file not found: {}".format(env_path))
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def resolve_provider_config(base_url="", api_key="", model="", env_file=""):
    file_env = load_env_file(env_file)
    resolved_base_url = str(
        base_url or file_env.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or ""
    ).strip()
    resolved_api_key = str(
        api_key or file_env.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    ).strip()
    resolved_model = str(
        model
        or file_env.get("UITARS_MODEL")
        or os.environ.get("UITARS_MODEL")
        or os.environ.get("OPENAI_MODEL")
        or "gpt-5.4"
    ).strip()
    if not resolved_base_url:
        raise ValueError("base_url is required")
    if not resolved_api_key:
        raise ValueError("api_key is required")
    return {
        "base_url": resolved_base_url,
        "api_key": resolved_api_key,
        "model": resolved_model,
    }


def build_evidence_bundle(mining_cases, transition_artifact, casebook_text):
    transition_summary = dict((transition_artifact or {}).get("summary") or {})
    if mining_cases:
        gap_ids = [str(row.get("gap_id") or "").strip() for row in mining_cases if row.get("gap_id")]
        return {
            "mode": "mining_cases",
            "num_cases": len(mining_cases),
            "cases": list(mining_cases),
            "transition_counts": dict(transition_summary.get("transition_counts") or {}),
            "required_gap_phrases": unique_phrases(required_gap_phrases_from_gap_ids(gap_ids)),
            "casebook_excerpt": extract_casebook_excerpt(casebook_text),
        }

    fallback_cases = build_transition_casebook_fallback_cases(transition_artifact)
    fallback_gap_ids = [str(row.get("gap_id") or "").strip() for row in fallback_cases if row.get("gap_id")]
    return {
        "mode": "transition_casebook_fallback",
        "num_cases": len(fallback_cases),
        "cases": fallback_cases,
        "transition_counts": dict(transition_summary.get("transition_counts") or {}),
        "required_gap_phrases": unique_phrases(required_gap_phrases_from_gap_ids(fallback_gap_ids)),
        "casebook_excerpt": extract_casebook_excerpt(casebook_text),
    }


def build_transition_casebook_fallback_cases(transition_artifact, max_cases=4):
    rows = [
        row
        for row in list((transition_artifact or {}).get("rows") or [])
        if str(row.get("transition") or "") in set(["lost", "both_fail"])
    ]
    if not rows:
        rows = list((transition_artifact or {}).get("rows") or [])[: int(max_cases or 0)]
    comparison = dict((transition_artifact or {}).get("comparison") or {})
    left_label = str(comparison.get("left_label") or "")
    right_label = str(comparison.get("right_label") or "")
    cases = []
    for row in rows[: int(max_cases or 0)]:
        gap_id = infer_fallback_gap_id(row)
        cases.append(build_mining_case(row, gap_id, left_label, right_label))
    return cases


def infer_fallback_gap_id(row):
    start_url = urllib.parse.unquote(str(row.get("start_url") or "").lower())
    left_urls = [
        urllib.parse.unquote(str(step.get("url") or "").lower())
        for step in list(row.get("left_trace_excerpt") or [])
    ]
    right_urls = [
        urllib.parse.unquote(str(step.get("url") or "").lower())
        for step in list(row.get("right_trace_excerpt") or [])
    ]
    expected_query = extract_query_fragment(start_url)
    if not expected_query:
        for url in left_urls:
            expected_query = extract_query_fragment(url)
            if expected_query:
                break
    if "next=" in start_url and any("release_lookup" in url for url in right_urls):
        return "login_next_lost"
    if "next=" in start_url and expected_query and right_urls and not any(
        expected_query in url for url in right_urls
    ):
        return "login_next_lost"
    if expected_query and any(expected_query in url for url in right_urls):
        later_actions = [str(step.get("action") or "").lower() for step in list(row.get("right_trace_excerpt") or [])[1:]]
        if any(action.startswith(("click", "goto", "noop")) for action in later_actions):
            return "query_state_finalization_missed"
    return "target_reached_but_no_final_answer"


def extract_query_fragment(url):
    text = str(url or "")
    if "?q=" in text:
        return text.split("?q=", 1)[1]
    if "&q=" in text:
        return text.split("&q=", 1)[1]
    return ""


def required_gap_phrases_from_gap_ids(gap_ids):
    phrases = []
    for gap_id in gap_ids:
        gap = str(gap_id or "").strip()
        if gap == "login_next_lost":
            phrases.extend(["login next", "filtered bookmark"])
        elif gap == "query_state_finalization_missed":
            phrases.extend(["filtered bookmark", "query-state"])
        elif gap == "target_reached_but_no_final_answer":
            phrases.append("final answer")
        elif gap == "hidden_click_repeated":
            phrases.append("hidden click")
        elif gap == "noninteractive_mark_clicked":
            phrases.append("non-interactive")
    return phrases


def extract_casebook_excerpt(casebook_text, max_lines=8):
    lines = str(casebook_text or "").splitlines()
    start_index = 0
    for index, line in enumerate(lines):
        if line.strip() == "## Representative `lost` Excerpts":
            start_index = index
            break
    excerpt = lines[start_index : start_index + int(max_lines or 0)]
    return "\n".join(excerpt).strip()


def build_candidate_prompt(base_rules, manifest, evidence):
    prompt = {
        "task": "Propose compact cross-version reflection rulebook edits for Linkding v2.4.1.",
        "constraints": [
            "Return only JSON with keys summary and proposals.",
            "summary must include preserve_patterns, lost_patterns, and required_gap_phrases.",
            "Allowed proposal operations: add_rule, edit_rule, keep_rule, drop_rule.",
            "For add_rule and edit_rule include title, scope, trigger, adaptation_strategy, verification_check, forbidden_actions.",
            "Keep rules mechanism-level and cross-task. Do not emit task_ids.",
            "Preserve successful v2.4 behaviors while repairing the Focus20 first_modified -> hardv3 regressions.",
        ],
        "response_schema": {
            "summary": {
                "preserve_patterns": ["..."],
                "lost_patterns": ["..."],
                "required_gap_phrases": ["..."],
            },
            "proposals": [
                {
                    "operation": "edit_rule",
                    "target_rule_id": "existing_rule_id",
                    "reason": "why this helps",
                    "rule": {},
                    "support": {"gap_ids": [], "supporting_task_ids": []},
                }
            ],
        },
        "base_rules": list(base_rules or []),
        "evidence": evidence,
        "manifest_summary": summarize_manifest(manifest),
    }
    return json.dumps(prompt, indent=2, sort_keys=True)


def summarize_manifest(manifest):
    if not isinstance(manifest, dict):
        return {}
    out = {}
    for dataset in ["focus20", "taskbank36"]:
        variants = manifest.get(dataset)
        if not isinstance(variants, dict):
            continue
        out[dataset] = {}
        for variant, rows in variants.items():
            if not isinstance(rows, dict):
                continue
            out[dataset][variant] = sorted(rows.keys())
    return out


def unique_phrases(rows):
    seen = set()
    out = []
    for row in list(rows or []):
        phrase = str(row or "").strip().lower()
        if phrase and phrase not in seen:
            seen.add(phrase)
            out.append(phrase)
    return out


def _as_dict(value):
    if isinstance(value, dict):
        return dict(value)
    return {}


if __name__ == "__main__":
    raise SystemExit(main())
