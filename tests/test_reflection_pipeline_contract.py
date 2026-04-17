import importlib
import inspect


def test_reflection_pipeline_modules_are_public_and_repo_local():
    package = importlib.import_module("linkding_xvr_minimal.rule_pipeline")

    for name in [
        "reflection_cases",
        "reflection_compare",
        "reflection_gaps",
        "reflection_merge",
        "reflection_proposals",
        "reflection_verify",
    ]:
        assert name in package.__all__
        module = importlib.import_module("linkding_xvr_minimal.rule_pipeline.{}".format(name))
        source = inspect.getsource(module)
        assert "webevolve" not in source
        assert "ExperienceStore" not in source
        assert "websites/" not in source
