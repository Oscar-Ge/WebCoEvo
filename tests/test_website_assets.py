from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_website_generation_assets_are_bundled():
    required_paths = [
        ROOT / "websites" / "original" / "linkding_1_45_0_control_snapshots" / "_html" / "control_access_login.html",
        ROOT / "websites" / "original" / "linkding_1_45_0_control_snapshots" / "control_surface_bookmarks.png",
        ROOT / "websites" / "first_modified" / "variant_templates" / "surface" / "templates" / "shared" / "layout.html",
        ROOT / "websites" / "first_modified" / "variant_templates" / "access" / "templates" / "registration" / "login.html",
        ROOT / "websites" / "first_modified" / "report" / "assets" / "surface_before_after.png",
        ROOT / "websites" / "hardv3" / "variant_templates" / "common" / "templates" / "shared" / "hardv3_release_grounded_body.html",
        ROOT / "websites" / "hardv3" / "variant_templates" / "access" / "templates" / "registration" / "login.html",
        ROOT / "websites" / "hardv3" / "report_v1" / "_html" / "surface_after.html",
    ]

    missing = [str(path.relative_to(ROOT)) for path in required_paths if not path.exists()]

    assert missing == []


def test_first_modified_and_hardv3_templates_are_distinct_generations():
    first_surface = (
        ROOT
        / "websites"
        / "first_modified"
        / "variant_templates"
        / "surface"
        / "templates"
        / "shared"
        / "layout.html"
    ).read_text(encoding="utf-8")
    hardv3_surface = (
        ROOT
        / "websites"
        / "hardv3"
        / "variant_templates"
        / "surface"
        / "templates"
        / "shared"
        / "layout.html"
    ).read_text(encoding="utf-8")

    assert "Visual refresh active" in first_surface
    assert "hardv3-release-grounded" not in first_surface
    assert "hardv3-release-grounded" in hardv3_surface
