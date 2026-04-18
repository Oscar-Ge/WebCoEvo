#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.rule_pipeline.reflection_verify import build_verification_report


REPORT_FILENAME = "2026-04-18-gpt54-v2_4_1-reflection-hardening-report.md"
PROMOTION_PACKET_FILENAME = "promotion_packet.json"


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-dir", default=str(ROOT))
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    root_dir = Path(args.root_dir).resolve()
    artifacts_dir = root_dir / "artifacts" / "reflection" / "v2_4_1"
    docs_dir = root_dir / "docs" / "reports"
    rulebooks_dir = root_dir / "rulebooks"
    configs_dir = root_dir / "configs"

    api_smoke = load_json(artifacts_dir / "api_smoke.json")
    focus20_transition = load_json(artifacts_dir / "focus20_transition_first_modified_to_hardv3.json")
    taskbank36_transition = load_json(artifacts_dir / "taskbank36_transition_first_modified_to_hardv3.json")
    casebook_text = read_text_if_exists(artifacts_dir / "focus20_casebook.md")
    candidate_summary = load_json(artifacts_dir / "gpt54_candidate_summary.json")
    base_rulebook = load_json(rulebooks_dir / "v2_4.json")
    candidate_rulebook = load_json(rulebooks_dir / "v2_4_1.json")
    raw_provider_output = load_optional_json(artifacts_dir / "gpt54_proposals_raw.json")

    verification = build_optional_verification(
        candidate_rulebook=candidate_rulebook,
        rulebook_path=rulebooks_dir / "v2_4_1.json",
        task_file=configs_dir / "focus20_hardv3_full.raw.json",
    )
    rule_delta = build_rule_delta(base_rulebook, candidate_rulebook)
    compatibility_note = build_compatibility_note(api_smoke, raw_provider_output)

    report_text = render_report_markdown(
        api_smoke=api_smoke,
        focus20_transition=focus20_transition,
        taskbank36_transition=taskbank36_transition,
        casebook_text=casebook_text,
        candidate_summary=candidate_summary,
        rule_delta=rule_delta,
        compatibility_note=compatibility_note,
        verification=verification,
    )

    docs_dir.mkdir(parents=True, exist_ok=True)
    report_path = docs_dir / REPORT_FILENAME
    report_path.write_text(report_text, encoding="utf-8")

    promotion_packet = {
        "schema_version": "webcoevo-linkding-v241-promotion-packet-v1",
        "candidate_version": str(candidate_rulebook.get("version") or "v2_4_1"),
        "api_smoke": api_smoke,
        "focus20": {
            "transition_counts": transition_counts(focus20_transition),
            "num_rows": transition_num_rows(focus20_transition),
        },
        "taskbank36": {
            "transition_counts": transition_counts(taskbank36_transition),
            "num_rows": transition_num_rows(taskbank36_transition),
        },
        "candidate_summary": candidate_summary,
        "verification": verification,
        "rule_delta": rule_delta,
        "compatibility_note": compatibility_note,
        "report_path": str(report_path),
        "rulebook_path": str(rulebooks_dir / "v2_4_1.json"),
    }
    packet_path = artifacts_dir / PROMOTION_PACKET_FILENAME
    packet_path.write_text(json.dumps(promotion_packet, indent=2, sort_keys=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "promotion_packet": str(packet_path),
                "verification_ok": bool((verification or {}).get("ok", False)),
            },
            sort_keys=True,
        )
    )
    return 0


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_optional_json(path):
    input_path = Path(path)
    if not input_path.exists():
        return {}
    return load_json(input_path)


def read_text_if_exists(path):
    input_path = Path(path)
    if not input_path.exists():
        return ""
    return input_path.read_text(encoding="utf-8")


def transition_counts(payload):
    return dict(((payload or {}).get("summary") or {}).get("transition_counts") or {})


def transition_num_rows(payload):
    return int((((payload or {}).get("summary") or {}).get("num_rows") or 0))


def build_optional_verification(candidate_rulebook, rulebook_path, task_file):
    if not Path(rulebook_path).exists() or not Path(task_file).exists():
        return {
            "ok": False,
            "skipped": True,
            "reason": "verification_inputs_missing",
        }
    return build_verification_report(
        candidate_rulebook,
        task_file=str(task_file),
        rulebook_path=str(rulebook_path),
        max_rules=8,
        no_task_scopes=True,
        required_gap_phrases=list(candidate_rulebook.get("required_gap_phrases") or []),
        rule_limit=8,
    )


def build_rule_delta(base_rulebook, candidate_rulebook):
    base_rules = {str(rule.get("rule_id") or ""): rule for rule in list(base_rulebook.get("rules") or []) if isinstance(rule, dict)}
    candidate_rules = [rule for rule in list(candidate_rulebook.get("rules") or []) if isinstance(rule, dict)]
    changed = []
    added = []
    seen_sources = set()
    for rule in candidate_rules:
        source_rule_id = str(rule.get("source_rule_id") or "").strip()
        if source_rule_id and source_rule_id in base_rules:
            seen_sources.add(source_rule_id)
            if rules_differ(base_rules[source_rule_id], rule):
                changed.append(
                    {
                        "source_rule_id": source_rule_id,
                        "candidate_rule_id": str(rule.get("rule_id") or ""),
                        "base_title": str(base_rules[source_rule_id].get("title") or ""),
                        "candidate_title": str(rule.get("title") or ""),
                    }
                )
        else:
            added.append(
                {
                    "candidate_rule_id": str(rule.get("rule_id") or ""),
                    "candidate_title": str(rule.get("title") or ""),
                }
            )
    dropped = []
    for rule_id, rule in sorted(base_rules.items()):
        if rule_id not in seen_sources:
            dropped.append({"source_rule_id": rule_id, "base_title": str(rule.get("title") or "")})
    return {
        "base_rule_count": len(base_rules),
        "candidate_rule_count": len(candidate_rules),
        "edited_rule_count": len(changed),
        "added_rule_count": len(added),
        "dropped_rule_count": len(dropped),
        "changed_rules": changed,
        "added_rules": added,
        "dropped_rules": dropped,
    }


def rules_differ(base_rule, candidate_rule):
    compare_keys = [
        "title",
        "scope",
        "trigger",
        "adaptation_strategy",
        "verification_check",
        "forbidden_actions",
    ]
    for key in compare_keys:
        if normalize_for_compare(base_rule.get(key)) != normalize_for_compare(candidate_rule.get(key)):
            return True
    return False


def normalize_for_compare(value):
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    if isinstance(value, list):
        return json.dumps(value, sort_keys=True)
    return str(value or "").strip()


def build_compatibility_note(api_smoke, raw_provider_output):
    generation_endpoint = str(api_smoke.get("generation_endpoint") or "")
    attempts = list(raw_provider_output.get("attempts") or [])
    if attempts:
        empty_attempts = [
            attempt.get("transport")
            for attempt in attempts
            if attempt.get("status") == 200 and attempt.get("empty_text")
        ]
        if generation_endpoint == "responses_stream" and empty_attempts:
            return (
                "ASXS was usable in this run, but only after using curl-like request headers and "
                "falling back to /responses streaming. The provider returned HTTP 200 with empty "
                "text for {} before the streaming fallback produced usable content."
            ).format(", ".join(str(row) for row in empty_attempts))
    if generation_endpoint:
        return "ASXS generation succeeded through `{}`.".format(generation_endpoint)
    return "ASXS compatibility details were not available in the report inputs."


def render_report_markdown(
    api_smoke,
    focus20_transition,
    taskbank36_transition,
    casebook_text,
    candidate_summary,
    rule_delta,
    compatibility_note,
    verification,
):
    focus_counts = transition_counts(focus20_transition)
    taskbank_counts = transition_counts(taskbank36_transition)
    required_gap_phrases = list(candidate_summary.get("required_gap_phrases") or [])
    preserve_patterns = list(((candidate_summary or {}).get("provider_summary") or {}).get("preserve_patterns") or [])
    lost_patterns = list(((candidate_summary or {}).get("provider_summary") or {}).get("lost_patterns") or [])

    lines = [
        "# GPT-5.4 V2.4.1 Reflection Hardening Report",
        "",
        "## API smoke status",
        "- Provider usable: `{}`".format(bool(api_smoke.get("ok"))),
        "- Generation endpoint: `{}`".format(str(api_smoke.get("generation_endpoint") or "")),
        "- Models available: `{}`".format(bool(api_smoke.get("provider_models_ok"))),
        "- Response excerpt: `{}`".format(str(api_smoke.get("response_excerpt") or "")),
        "- Compatibility note: {}".format(compatibility_note),
        "",
        "## Focus20 transition counts",
        "- `both_success`: {}".format(focus_counts.get("both_success", 0)),
        "- `lost`: {}".format(focus_counts.get("lost", 0)),
        "- `saved`: {}".format(focus_counts.get("saved", 0)),
        "- `both_fail`: {}".format(focus_counts.get("both_fail", 0)),
        "",
        "Transition explanations:",
        "- `old success -> new success`: preserve these successful V2.4 behaviors when drafting v2.4.1 rules.",
        "- `old success -> new fail`: treat these as regression evidence that the candidate must repair without overfitting.",
        "",
        "## TaskBank36 held-out summary",
        "- `both_success`: {}".format(taskbank_counts.get("both_success", 0)),
        "- `lost`: {}".format(taskbank_counts.get("lost", 0)),
        "- `saved`: {}".format(taskbank_counts.get("saved", 0)),
        "- `both_fail`: {}".format(taskbank_counts.get("both_fail", 0)),
        "",
        "## v2.4 -> v2.4.1 rule delta summary",
        "- Edited rules: {}".format(rule_delta.get("edited_rule_count", 0)),
        "- Added rules: {}".format(rule_delta.get("added_rule_count", 0)),
        "- Dropped rules: {}".format(rule_delta.get("dropped_rule_count", 0)),
        "- Proposal accepted/rejected: {}/{}".format(
            ((candidate_summary or {}).get("proposal_summary") or {}).get("accepted", 0),
            ((candidate_summary or {}).get("proposal_summary") or {}).get("rejected", 0),
        ),
        "- Evidence mode: `{}`".format(str(((candidate_summary or {}).get("evidence") or {}).get("mode") or "")),
        "- Required gap phrases: {}".format(", ".join(required_gap_phrases) if required_gap_phrases else "none"),
    ]

    if preserve_patterns:
        lines.extend(["", "Preserve patterns:"])
        for row in preserve_patterns[:3]:
            lines.append("- {}".format(row))

    if lost_patterns:
        lines.extend(["", "Lost patterns:"])
        for row in lost_patterns[:3]:
            lines.append("- {}".format(row))

    if rule_delta.get("changed_rules"):
        lines.extend(["", "Changed rules:"])
        for row in rule_delta["changed_rules"][:5]:
            lines.append(
                "- `{}` -> `{}`".format(
                    row.get("base_title", ""),
                    row.get("candidate_title", ""),
                )
            )

    lost_excerpt = extract_lost_excerpt(casebook_text)
    if lost_excerpt:
        lines.extend(["", "Focus20 lost-case excerpt:", lost_excerpt])

    lines.extend(
        [
            "",
            "## Verification",
            "- Verification ok: `{}`".format(bool((verification or {}).get("ok"))),
            "- Verification skipped: `{}`".format(bool((verification or {}).get("skipped"))),
        ]
    )
    if (verification or {}).get("coverage"):
        coverage = verification["coverage"]
        lines.append(
            "- Focus20 coverage: `{}/{} covered`".format(
                coverage.get("covered", 0),
                coverage.get("task_count", 0),
            )
        )

    return "\n".join(lines).strip() + "\n"


def extract_lost_excerpt(casebook_text):
    lines = str(casebook_text or "").splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "## Representative `lost` Excerpts":
            start = index
            break
    if start is None:
        return ""
    excerpt = []
    for line in lines[start : start + 4]:
        excerpt.append(line)
    return "\n".join(excerpt).strip()


if __name__ == "__main__":
    raise SystemExit(main())
