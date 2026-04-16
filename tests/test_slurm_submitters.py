from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hardv3_matrix_submitter_exposes_sbatch_time_override():
    text = (ROOT / "slurm" / "submit_hardv3_matrix.sh").read_text()

    assert 'SBATCH_TIME="${SBATCH_TIME:-04:00:00}"' in text
    assert '--time="${SBATCH_TIME}"' in text


def test_slurm_scripts_default_to_repo_root_not_parent_worktree():
    for name in (
        "submit_hardv3_matrix.sh",
        "run_hardv3_variant_singularity.slurm.sh",
        "run_smoke_access_singularity.slurm.sh",
    ):
        text = (ROOT / "slurm" / name).read_text()
        assert "minimal_linkding_xvr" not in text
        assert "linkding-v26-selective-merge" not in text
