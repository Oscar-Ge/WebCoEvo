# Generated Rulebooks

Use `rulebooks/generated/` for machine-produced artifacts that should remain auditable and separate from the bundled hand-curated rulebooks in `rulebooks/`.

Recommended layout:

```text
rulebooks/generated/<run-label>/
  episodes.json
  recovery.json
  expel_rules.json
  coverage_report.json
```

Recommended metadata for generated artifacts:

- `source_recovery_artifact`
- `source_cases`
- `rule_generation_records`
- `coverage_report`
- `summary`

For ExpeL-style rule files, keep provenance attached to each rule when possible:

- `source_task_ids`
- `provenance_episode_ids`
- `support_count`
- `evidence_mode`
- `version_tags`

The intent is not to recreate the old broad `webevolve` artifact tree. Keep these outputs small, Linkding-specific, and directly consumable by `linkding_xvr_minimal.runner`.
