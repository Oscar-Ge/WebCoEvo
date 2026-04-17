from pathlib import Path


def test_readme_documents_public_rule_pipeline_entrypoints():
    repo_root = Path(__file__).resolve().parents[1]
    readme = (repo_root / "README.md").read_text(encoding="utf-8")

    assert "scripts/build_episode_artifact.py" in readme
    assert "scripts/build_recovery_artifact.py" in readme
    assert "scripts/build_expel_rules_from_recovery.py" in readme
    assert "scripts/verify_rule_coverage.py" in readme
    assert "rulebooks/generated/" in readme
    assert "websites/" in readme
    assert "not the runtime authority" in readme


def test_generated_rulebooks_directory_has_readme():
    repo_root = Path(__file__).resolve().parents[1]
    readme_path = repo_root / "rulebooks" / "generated" / "README.md"

    assert readme_path.exists()
    text = readme_path.read_text(encoding="utf-8")
    assert "source_recovery_artifact" in text
    assert "rule_generation_records" in text
    assert "coverage_report" in text
