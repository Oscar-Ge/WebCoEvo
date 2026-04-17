import importlib
import inspect


def test_rule_pipeline_package_exports_expected_modules_without_legacy_dependencies():
    package = importlib.import_module("linkding_xvr_minimal.rule_pipeline")

    assert set(["coverage", "episodes", "induction", "recovery"]).issubset(set(package.__all__))

    for module_name in package.__all__:
        module = importlib.import_module(f"linkding_xvr_minimal.rule_pipeline.{module_name}")
        source = inspect.getsource(module)
        assert "webevolve" not in source
        assert "ExperienceStore" not in source
        assert "websites/" not in source
