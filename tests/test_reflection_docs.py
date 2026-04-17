from pathlib import Path


def test_readme_documents_public_reflection_rules_pipeline():
    repo_root = Path(__file__).resolve().parents[1]
    readme = (repo_root / "README.md").read_text(encoding="utf-8")

    for required in [
        "scripts/build_xvr_transition_artifact.py",
        "scripts/mine_reflection_gaps.py",
        "scripts/build_reflection_rules.py",
        "scripts/verify_reflection_rulebook.py",
        "scripts/build_reflection_delta_slice.py",
        "rulebooks/generated/",
        "Focus20",
        "TaskBank36",
        "websites/",
    ]:
        assert required in readme
    assert "Focus20 is the mining set" in readme
    assert "TaskBank36 is held out" in readme
    assert "websites/ is not the runtime source of truth" in readme


def test_generated_reflection_readme_documents_artifact_layout_and_policy():
    repo_root = Path(__file__).resolve().parents[1]
    readme = repo_root / "rulebooks" / "generated" / "reflection" / "README.md"

    assert readme.exists()
    text = readme.read_text(encoding="utf-8")
    for required in [
        "transition_artifact.json",
        "behavior_gaps.json",
        "mining_cases.jsonl",
        "candidate_rulebook.json",
        "verification_report.json",
        "delta_slice.raw.json",
        "promotion_decision.md",
        "Focus20",
        "TaskBank36",
    ]:
        assert required in text
    assert "Do not commit secrets" in text
