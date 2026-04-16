import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_compose_generator_writes_access_binds(tmp_path):
    out = tmp_path / "compose.access.yml"

    subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "docker" / "generate_local_compose.py"),
            "--variant",
            "access",
            "--host-port",
            "19103",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        check=True,
    )

    text = out.read_text(encoding="utf-8")

    assert "sissbruecker/linkding:1.45.0" in text
    assert '"19103:9090"' in text
    assert "hardv3_release_grounded_head.html" in text
    assert "hardv3_release_grounded_body.html" in text
    assert "templates/registration/login.html" in text
    assert "host.docker.internal:host-gateway" in text
    assert "Dockerfile.runner" in text


def test_docs_separate_hpc_and_local_docker_paths():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README-cn.md").read_text(encoding="utf-8")

    assert "HPC / Slurm Path" in readme
    assert "Local Docker Path" in readme
    assert "HPC / Slurm 路线" in readme_cn
    assert "本地 Docker 路线" in readme_cn


def test_repo_skills_cover_local_docker_and_hpc_boundary():
    run_skill = (ROOT / "skills" / "webcoevo-run" / "SKILL.md").read_text(encoding="utf-8")
    docker_skill = (ROOT / "skills" / "webcoevo-local-docker" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "HPC" in run_skill and "Slurm" in run_skill
    assert "Local Docker" in run_skill
    assert "docker compose" in docker_skill
    assert "Linux" in docker_skill and "macOS" in docker_skill
