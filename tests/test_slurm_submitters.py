from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hardv3_matrix_submitter_exposes_sbatch_time_override():
    text = (ROOT / "slurm" / "submit_hardv3_matrix.sh").read_text()

    assert 'SBATCH_TIME="${SBATCH_TIME:-04:00:00}"' in text
    assert '--time="${SBATCH_TIME}"' in text


def test_slurm_scripts_default_to_repo_root_not_parent_worktree():
    for name in (
        "submit_hardv3_matrix.sh",
        "submit_control_rules_matrix.sh",
        "submit_first_modified_rules_matrix.sh",
        "run_hardv3_variant_singularity.slurm.sh",
        "run_smoke_access_singularity.slurm.sh",
    ):
        text = (ROOT / "slurm" / name).read_text()
        assert "minimal_linkding_xvr" not in text
        assert "linkding-v26-selective-merge" not in text


def test_hardv3_runner_exposes_rule_and_task_profile_switches():
    text = (ROOT / "slurm" / "run_hardv3_variant_singularity.slurm.sh").read_text()

    assert 'REQUIRE_XVR_RULES="${REQUIRE_XVR_RULES:-1}"' in text
    assert 'REQUIRE_EXPEL_RULES="${REQUIRE_EXPEL_RULES:-1}"' in text
    assert 'TASK_HOST_PROFILE="${TASK_HOST_PROFILE:-variant}"' in text
    assert 'RUNTIME_VARIANTS="${RUNTIME_VARIANTS:-${DRIFT_VARIANTS}}"' in text
    assert 'TASK_LIMIT="${TASK_LIMIT:-0}"' in text
    assert 'webAgentBenchmark/.venv/bin/python' in text
    assert 'PYTHON_BIN="$(command -v python3 || true)"' in text
    assert "runner_args+=(--fail-on-empty-xvr-rules)" in text


def test_control_rules_submitter_exports_clean_baseline_flags():
    text = (ROOT / "slurm" / "submit_control_rules_matrix.sh").read_text()

    assert 'LINKDING_DRIFT_PROFILE="control"' in text
    assert 'RUNTIME_VARIANTS="control"' in text
    assert "TASK_HOST_PROFILE=control" in text
    assert 'RULEBOOK="${rulebook}"' in text
    assert 'REQUIRE_XVR_RULES="${require_xvr}"' in text
    assert 'REQUIRE_EXPEL_RULES="${require_expel}"' in text
    assert 'TASK_LIMIT="${TASK_LIMIT}"' in text
    assert 'expel_rule_file=""' in text


def test_first_modified_submitter_exports_profile_and_shard_overrides():
    text = (ROOT / "slurm" / "submit_first_modified_rules_matrix.sh").read_text()

    assert 'LINKDING_DRIFT_PROFILE="${LINKDING_DRIFT_PROFILE:-first_modified}"' in text
    assert 'SHARD_NAMES_CSV="${SHARD_NAMES_CSV:-access,surface,content,runtime_process,structural_functional}"' in text
    assert 'SHARD_VARIANTS_CSV="${SHARD_VARIANTS_CSV:-access,surface,content,runtime:process,structural:functional}"' in text
    assert "TASK_HOST_PROFILE=variant" in text
    assert 'RUNTIME_VARIANTS="${drift_variants}"' in text
    assert 'REQUIRE_XVR_RULES="${require_xvr}"' in text
    assert 'TASK_LIMIT="${TASK_LIMIT}"' in text
