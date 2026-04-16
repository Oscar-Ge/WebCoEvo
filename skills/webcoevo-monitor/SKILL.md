---
name: webcoevo-monitor
description: Monitor WebCoEvo Linkding XVR experiments. Use when checking Slurm job status, inspecting smoke/full matrix logs, diagnosing failed or timed-out shards, auditing trace JSONL files for injected ExpeL and cross-version reflection rules, or deciding which shards need reruns.
---

# WebCoEvo Monitor

## Queue

Check active jobs:

```bash
squeue --me -o '%i|%j|%T|%M|%L'
```

Check accounting for known IDs:

```bash
sacct -j <job_ids> --format=JobID,JobName%30,State,Elapsed,ExitCode -P
```

Treat `FAILED`, `TIMEOUT`, and `CANCELLED` separately from agent task failure. A reset/login error is infrastructure; an unsuccessful eval row with normal trace export is model/task behavior.

## Logs

Matrix logs live under `results/slurm_logs/<run_stamp>/` when launched by `submit_hardv3_matrix.sh`.

For a running job:

```bash
tail -n 120 results/slurm_logs/<run_stamp>/<job>-<id>.log
```

Confirm the log says:

- runtime path points to the intended `LINKDING_DRIFT_BASE_DIR`
- `task_count` matches the shard
- no `OPENAI_API_KEY` or Python executable error
- trace audit runs after AgentLab export

## Trace Audit

Run the bundled audit script:

```bash
python3 scripts/verify_trace_rules.py \
  --trace 'results/<run_label>/shard_<name>/run_<stamp>/*trace*.jsonl' \
  --require-cross-version-rules \
  --require-rulebook-path \
  --require-expel-rules
```

A valid trace contains:

- `cross_version_reflection_rule_ids`
- `cross_version_reflection_rules_path`
- `injected_rule_ids`

Reset-error rows should still contain those fields due to preflight backfill.

## Rerun Policy

Rerun only the affected shard when:

- Slurm state is `FAILED` or `TIMEOUT`
- trace audit fails
- `task_count` is wrong for the intended shard
- runtime path points to the wrong storage area

Keep old successful shards out of paper comparisons if their runner commit, task file, or rule injection semantics differ.
