# GPT-5.4 V2.4.1 Reflection Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Validate the OpenAI-compatible `gpt-5.4` endpoint, then use it to build an evidence-grounded `v2.4.1` Linkding reflection rulebook that explains and repairs the `first_modified -> hardv3` regression.

**Architecture:** Reuse the existing reflection pipeline instead of inventing a new one. The implementation should: resolve the exact run artifacts for `first_modified` and `hardv3`, build matched transition and mining-case artifacts from `Focus20`, call GPT-5.4 only through the existing OpenAI-compatible proposal path plus a small API smoke checker, merge accepted edits onto [`rulebooks/v2_4.json`](/home/gecm/WebCoEvo/rulebooks/v2_4.json), and finally verify and evaluate `v2.4.1` with clean no-regression gates.

**Tech Stack:** Python `argparse`/`json`/`pathlib`/`urllib`, existing `scripts/build_xvr_transition_artifact.py`, `scripts/mine_reflection_gaps.py`, `scripts/build_reflection_rules.py`, `scripts/verify_reflection_rulebook.py`, pytest, Slurm, OpenAI-compatible `chat/completions`.

---

## Preconditions

- Treat `Focus20` as the primary mining surface.
- Treat `TaskBank36` as held-out validation and reporting only.
- Compare the actual website progression `v1.45.0 -> first_modified -> hardv3`.
- Start from these existing result families:
  - `results/focus20_first_modified_v2_4_expel_official_minimal_v1/...`
  - `results/focus20_hardv3_v2_4_expel_official_minimal_v1/...`
  - `results/taskbank36_first_modified_v2_4_expel_official_minimal_v1/...`
  - `results/taskbank36_hardv3_v2_4_expel_official_minimal_v1/...`
  - Optional auxiliary contrast: `*_expel_only_official_minimal_v1`
- Save new derived artifacts under `artifacts/reflection/v2_4_1/`.

## Task 1: Add GPT-5.4 Compatibility Smoke Check

**Files:**
- Create: `scripts/check_openai_compat.py`
- Create: `tests/test_check_openai_compat.py`

**Step 1: Write the failing test**

Create `tests/test_check_openai_compat.py` with coverage for:

- normalizing `base_url` so `https://api.asxs.top/v1` becomes:
  - `.../models`
  - `.../chat/completions`
- parsing a successful `/models` payload
- parsing a successful `chat.completions` payload
- returning a structured failure report when the model is unavailable or the provider returns non-JSON text

Minimal test shape:

```python
def test_normalize_endpoints_and_extract_chat_message():
    report = parse_chat_response(
        {"choices": [{"message": {"content": "ok"}}]}
    )
    assert report["content"] == "ok"
```

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_check_openai_compat.py -q
```

Expected: FAIL because the helper script does not exist.

**Step 3: Implement the smoke checker**

Create `scripts/check_openai_compat.py` to:

- accept `--base-url`, `--api-key`, `--model`, `--output-file`
- call `GET /models` if available
- call `POST /chat/completions` with a tiny prompt such as `"Reply with OK only."`
- save a structured JSON report:

```json
{
  "ok": true,
  "provider_models_ok": true,
  "chat_ok": true,
  "model": "gpt-5.4",
  "base_url": "https://api.asxs.top/v1",
  "response_excerpt": "OK"
}
```

**Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_check_openai_compat.py -q
```

Expected: PASS.

**Step 5: Run the real smoke check**

Run:

```bash
python3 scripts/check_openai_compat.py \
  --base-url "https://api.asxs.top/v1" \
  --api-key "$OPENAI_API_KEY" \
  --model "gpt-5.4" \
  --output-file artifacts/reflection/v2_4_1/api_smoke.json
```

Expected: `ok=true` and `chat_ok=true`.

**Step 6: Commit checkpoint**

```bash
git add scripts/check_openai_compat.py tests/test_check_openai_compat.py
git commit -m "feat: add openai-compatible api smoke checker"
```

## Task 2: Freeze the V2.4 Regression Input Manifest

**Files:**
- Create: `scripts/build_linkding_v241_manifest.py`
- Create: `tests/test_build_linkding_v241_manifest.py`

**Step 1: Write the failing test**

Create tests that feed a fake `results/` tree and assert the manifest resolves:

- `Focus20 first_modified v2.4`
- `Focus20 hardv3 v2.4`
- `TaskBank36 first_modified v2.4`
- `TaskBank36 hardv3 v2.4`
- optional `expel_only` companions when present

The test should assert each entry contains:

```python
{
    "eval_path": "...jsonl",
    "trace_path": "...jsonl",
    "run_dir": "...",
}
```

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_build_linkding_v241_manifest.py -q
```

Expected: FAIL because the manifest builder does not exist.

**Step 3: Implement the manifest builder**

Create `scripts/build_linkding_v241_manifest.py` to scan `results/` and emit:

`artifacts/reflection/v2_4_1/run_manifest.json`

The manifest should record exact paths for:

- `focus20.first_modified.v2_4`
- `focus20.hardv3.v2_4`
- `taskbank36.first_modified.v2_4`
- `taskbank36.hardv3.v2_4`
- optional `expel_only` mirrors

It should fail loudly if any required `v2_4` run is missing.

**Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_build_linkding_v241_manifest.py -q
```

Expected: PASS.

**Step 5: Build the real manifest**

Run:

```bash
python3 scripts/build_linkding_v241_manifest.py \
  --results-root results \
  --output-file artifacts/reflection/v2_4_1/run_manifest.json
```

Expected: JSON with the four required V2.4 run pairs.

**Step 6: Commit checkpoint**

```bash
git add scripts/build_linkding_v241_manifest.py tests/test_build_linkding_v241_manifest.py
git commit -m "feat: add v2.4.1 run manifest builder"
```

## Task 3: Build Focus20-First Matched Evidence and Casebook

**Files:**
- Create: `scripts/build_linkding_v241_casebook.py`
- Create: `tests/test_build_linkding_v241_casebook.py`

**Step 1: Write the failing test**

Create a test that uses a tiny manifest and asserts the casebook builder writes:

- `focus20_transition_first_modified_to_hardv3.json`
- `focus20_behavior_gaps.json`
- `focus20_mining_cases.jsonl`
- `focus20_delta_manifest.json`
- `focus20_casebook.md`

The test should verify `focus20_casebook.md` includes:

- `both_success`
- `lost`
- a short explanation block for:
  - `old success -> new success`
  - `old success -> new fail`

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_build_linkding_v241_casebook.py -q
```

Expected: FAIL because the orchestration script does not exist.

**Step 3: Implement the casebook builder**

Create `scripts/build_linkding_v241_casebook.py` to:

- read `artifacts/reflection/v2_4_1/run_manifest.json`
- call existing CLIs or imported helpers from:
  - `scripts/build_xvr_transition_artifact.py`
  - `scripts/mine_reflection_gaps.py`
  - `scripts/build_reflection_delta_slice.py`
- render a compact markdown casebook with:
  - transition counts
  - top behavior gaps
  - representative `both_success` excerpts
  - representative `lost` excerpts
  - task IDs supporting each gap

Use `configs/focus20_hardv3_full.raw.json` as the canonical task file for transition alignment.

**Step 4: Add held-out summary**

Also emit a lightweight held-out summary for:

- `taskbank36_transition_first_modified_to_hardv3.json`
- `taskbank36_casebook.md`

Do not use TaskBank36 to generate rule text; use it only for later validation/reporting.

**Step 5: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_build_linkding_v241_casebook.py -q
```

Expected: PASS.

**Step 6: Build the real casebook**

Run:

```bash
python3 scripts/build_linkding_v241_casebook.py \
  --manifest-file artifacts/reflection/v2_4_1/run_manifest.json \
  --focus20-task-file configs/focus20_hardv3_full.raw.json \
  --taskbank-task-file configs/taskbank36_hardv3_full.raw.json \
  --output-dir artifacts/reflection/v2_4_1
```

Expected: Focus20 and TaskBank36 casebooks plus mined cases.

**Step 7: Commit checkpoint**

```bash
git add scripts/build_linkding_v241_casebook.py tests/test_build_linkding_v241_casebook.py
git commit -m "feat: add v2.4.1 matched evidence casebook builder"
```

## Task 4: Generate the GPT-5.4 Candidate Rulebook

**Files:**
- Create: `scripts/build_linkding_v241_candidate.py`
- Create: `tests/test_build_linkding_v241_candidate.py`
- Modify: `tests/test_reflection_proposals.py`
- Optional modify only if needed: `linkding_xvr_minimal/rule_pipeline/reflection_proposals.py`

**Step 1: Write the failing tests**

Create tests for:

- reading `focus20_mining_cases.jsonl`
- calling the existing proposal pipeline with a stubbed GPT response
- writing `rulebooks/v2_4_1.json`
- saving the raw LLM response and parsed proposal summary
- tolerating JSON wrapped in fenced blocks or extra prose

If provider-specific output breaks current parsing, extend `tests/test_reflection_proposals.py` first.

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_build_linkding_v241_candidate.py tests/test_reflection_proposals.py -q
```

Expected: FAIL because the candidate builder does not exist yet.

**Step 3: Implement the candidate builder**

Create `scripts/build_linkding_v241_candidate.py` to:

- read:
  - `artifacts/reflection/v2_4_1/api_smoke.json`
  - `artifacts/reflection/v2_4_1/focus20_mining_cases.jsonl`
  - `artifacts/reflection/v2_4_1/focus20_casebook.md`
  - [`rulebooks/v2_4.json`](/home/gecm/WebCoEvo/rulebooks/v2_4.json)
- abort if `api_smoke.json` says `chat_ok=false`
- call the same OpenAI-compatible provider with `model=gpt-5.4`
- reuse `build_reflection_rules.py` logic or import the same proposal helpers
- write:
  - `rulebooks/v2_4_1.json`
  - `artifacts/reflection/v2_4_1/gpt54_proposals_raw.json`
  - `artifacts/reflection/v2_4_1/gpt54_candidate_summary.json`

The summary file should include:

- top `both_success` patterns GPT thinks should be preserved
- top `lost` patterns GPT thinks caused regressions
- accepted/rejected proposal counts

**Step 4: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_build_linkding_v241_candidate.py tests/test_reflection_proposals.py -q
```

Expected: PASS.

**Step 5: Generate the real candidate**

Run:

```bash
python3 scripts/build_linkding_v241_candidate.py \
  --base-url "https://api.asxs.top/v1" \
  --api-key "$OPENAI_API_KEY" \
  --model "gpt-5.4" \
  --base-rulebook rulebooks/v2_4.json \
  --manifest-file artifacts/reflection/v2_4_1/run_manifest.json \
  --casebook-file artifacts/reflection/v2_4_1/focus20_casebook.md \
  --mining-cases artifacts/reflection/v2_4_1/focus20_mining_cases.jsonl \
  --output-rulebook rulebooks/v2_4_1.json \
  --output-dir artifacts/reflection/v2_4_1
```

Expected: `rulebooks/v2_4_1.json` plus raw GPT outputs.

**Step 6: Commit checkpoint**

```bash
git add scripts/build_linkding_v241_candidate.py tests/test_build_linkding_v241_candidate.py tests/test_reflection_proposals.py rulebooks/v2_4_1.json
git commit -m "feat: generate gpt-5.4-based v2.4.1 rulebook candidate"
```

## Task 5: Verify Rulebook Contract and Coverage

**Files:**
- Create: `tests/test_v241_rulebook_contract.py`
- Optional modify only if coverage holes appear: `rulebooks/v2_4_1.json`

**Step 1: Write the failing test**

Create a test that:

- loads `rulebooks/v2_4_1.json`
- asserts it passes contract checks similar to `scripts/verify_reflection_rulebook.py`
- asserts there are no task-scoped rules unless explicitly approved
- asserts at least one rule addresses each top mined gap phrase from the Focus20 casebook

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_v241_rulebook_contract.py -q
```

Expected: FAIL until the candidate exists and is valid.

**Step 3: Implement or adjust the candidate**

If the candidate fails because GPT returned malformed or too-specific rules:

- fix the proposal wrapper or parser first
- regenerate `rulebooks/v2_4_1.json`
- keep the raw GPT response for auditability

**Step 4: Run CLI verification**

Run:

```bash
python3 scripts/verify_reflection_rulebook.py \
  --task-file configs/focus20_hardv3_full.raw.json \
  --rulebook rulebooks/v2_4_1.json \
  --no-task-scopes \
  --json
```

Expected: `ok=true`.

**Step 5: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_v241_rulebook_contract.py -q
```

Expected: PASS.

**Step 6: Commit checkpoint**

```bash
git add tests/test_v241_rulebook_contract.py rulebooks/v2_4_1.json
git commit -m "test: verify v2.4.1 rulebook contract"
```

## Task 6: Generate Report and Promotion Packet

**Files:**
- Create: `scripts/reporting/generate_linkding_v241_report.py`
- Create: `tests/test_generate_linkding_v241_report.py`

**Step 1: Write the failing test**

Create a report test that feeds small fake artifacts and asserts the generated markdown contains:

- API smoke status
- `Focus20` transition counts
- `TaskBank36` held-out summary
- `old success -> new success` explanation
- `old success -> new fail` explanation
- `v2.4 -> v2.4.1` rule delta summary

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_generate_linkding_v241_report.py -q
```

Expected: FAIL because the report generator does not exist.

**Step 3: Implement the report generator**

Create `scripts/reporting/generate_linkding_v241_report.py` to read:

- `artifacts/reflection/v2_4_1/api_smoke.json`
- `artifacts/reflection/v2_4_1/focus20_transition_first_modified_to_hardv3.json`
- `artifacts/reflection/v2_4_1/taskbank36_transition_first_modified_to_hardv3.json`
- `artifacts/reflection/v2_4_1/focus20_casebook.md`
- `artifacts/reflection/v2_4_1/gpt54_candidate_summary.json`
- `rulebooks/v2_4.json`
- `rulebooks/v2_4_1.json`

and emit:

- `docs/reports/2026-04-18-gpt54-v2_4_1-reflection-hardening-report.md`
- `artifacts/reflection/v2_4_1/promotion_packet.json`

**Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_generate_linkding_v241_report.py -q
```

Expected: PASS.

**Step 5: Generate the real report**

Run:

```bash
python3 scripts/reporting/generate_linkding_v241_report.py
```

Expected: a markdown report ready to review before launching the eval matrix.

**Step 6: Commit checkpoint**

```bash
git add scripts/reporting/generate_linkding_v241_report.py tests/test_generate_linkding_v241_report.py docs/reports/2026-04-18-gpt54-v2_4_1-reflection-hardening-report.md
git commit -m "docs: add gpt-5.4 v2.4.1 reflection hardening report"
```

## Execution Notes

- Only after Tasks 1-6 pass should we launch smoke/full evaluation of `rulebooks/v2_4_1.json`.
- Evaluation order:
  1. `Focus20 first_modified` smoke
  2. `Focus20 hardv3` smoke
  3. `Focus20 first_modified` full
  4. `Focus20 hardv3` full
  5. `TaskBank36` held-out validation
- Promotion rule:
  - `hardv3` must improve materially over `v2.4`
  - `first_modified` must not regress materially
  - TaskBank36 may inform the report but should not retroactively rewrite the rule text unless Focus20 remains ambiguous
