import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "scripts" / "singularity" / "linkding_drift_manifest.py"


def run_manifest(profile, *args):
    env = os.environ.copy()
    if profile is None:
        env.pop("LINKDING_DRIFT_PROFILE", None)
    else:
        env["LINKDING_DRIFT_PROFILE"] = profile
    return subprocess.run(
        [sys.executable, str(MANIFEST), *args],
        cwd=str(ROOT),
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    ).stdout


def test_default_profile_keeps_hardv3_bind_mounts():
    out = run_manifest(None, "--variant", "surface", "--format", "binds")

    assert "scripts/singularity/linkding_drift/variants/surface/templates/shared/layout.html" in out
    assert "websites/first_modified" not in out


def test_first_modified_profile_uses_historical_template_binds():
    out = run_manifest("first_modified", "--variant", "surface", "--format", "binds")

    assert "websites/first_modified/variant_templates/surface/templates/shared/layout.html" in out
    assert "/etc/linkding/bookmarks/templates/shared/layout.html" in out
    assert "scripts/singularity/linkding_drift/variants/surface" not in out


def test_first_modified_profile_maps_all_base_variant_files():
    expected = {
        "access": "templates/registration/login.html",
        "surface": "templates/shared/layout.html",
        "content": "templates/tags/index.html",
        "structural": "templates/shared/nav_menu.html",
        "functional": "templates/bookmarks/bookmark_page.html",
        "process": "templates/bookmarks/new.html",
        "runtime": "templates/shared/layout.html",
    }

    for variant, relative_path in expected.items():
        out = run_manifest("first_modified", "--variant", variant, "--format", "binds")
        assert f"websites/first_modified/variant_templates/{variant}/{relative_path}" in out


def test_control_profile_removes_all_bind_mounts():
    for variant in ("control", "surface", "access"):
        out = run_manifest("control", "--variant", variant, "--format", "binds")
        assert out == ""
