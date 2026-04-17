# Generated Reflection Rule Artifacts

Use this directory layout for machine-produced cross-version reflection rule artifacts. Keep generated evidence separate from the bundled hand-curated rulebooks in `rulebooks/v2_4.json`, `rulebooks/v2_5.json`, and `rulebooks/v2_6.json`.

Recommended per-run layout:

```text
rulebooks/generated/<run-label>/reflection/
  transition_artifact.json
  capability_profile.json
  behavior_gaps.json
  mining_cases.jsonl
  rule_proposals.json
  candidate_rulebook.json
  verification_report.json
  delta_slice.raw.json
  delta_manifest.json
  promotion_decision.md
```

Artifact meanings:

- `transition_artifact.json`: matched left/right eval and trace comparison with saved, lost, both_success, both_fail, invalid_for_mining, and incomplete_run accounting.
- `capability_profile.json`: aggregate capability profile by drift type, variant, or source task.
- `behavior_gaps.json`: deterministic behavior-gap taxonomy with supporting and risk task IDs.
- `mining_cases.jsonl`: compact model-facing evidence packets for rule proposal generation.
- `rule_proposals.json`: structured add/edit/keep/drop proposal payload from a stub or OpenAI-compatible model endpoint.
- `candidate_rulebook.json`: deployable cross-version reflection rulebook compatible with `load_rulebook` and `select_rules`.
- `verification_report.json`: max-rule, required-field, no-task-scope, required-gap, and coverage checks.
- `delta_slice.raw.json`: runner-consumable task slice for must_keep, must_recover, regression_rails, and diagnostic_frontier buckets.
- `promotion_decision.md`: conservative promotion decision record.

Policy:

- Focus20 is the primary mining surface for reflection rule wording.
- TaskBank36 is held out for validation and should not be mined into deployable reflection rules by default.
- Deployable rulebooks should use drift/source-family level behavior rules, not task-specific patches, unless a debug mode explicitly allows task scope.
- Do not commit secrets, endpoint tokens, `.env.umich`, or raw API keys in generated artifacts.
- The `websites/` directory is archival review material. Runtime source of truth remains `scripts/singularity/linkding_drift/variants/`.
