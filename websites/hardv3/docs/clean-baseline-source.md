# Linkding hardv3 Clean Baseline Source

**Date:** 2026-04-13  
**Purpose:** Record the clean Linkding `v1.45.0` source baseline for hardv3 release-grounded website hardening.

## Baseline Image

| Field | Value |
|---|---|
| Linkding version | `1.45.0` |
| Singularity image | `/home/gecm/linkding-baselines/images/linkding_1450.sif` |
| SHA-256 | `0571f0ccf47429bc4f2b87cc7ba55de2207a71661ce5e5122c0b757987d7a84c` |
| Template root | `/etc/linkding/bookmarks/templates` |
| Template count | `46` |
| Captured template list | `/tmp/linkding_1450_templates_hardv3_baseline.txt` |

## Source Rule

hardv3 must start from the clean Linkding `v1.45.0` image/templates. It must not be implemented by editing or extending hardv2 route-gate behavior.

Allowed starting points:

- clean templates from `/etc/linkding/bookmarks/templates`;
- generic Singularity drift runtime helpers;
- minimal manifest wiring required to bind hardv3 overrides;
- release-grounded operator code written specifically for hardv3.

Forbidden inherited hardv2 markers:

- `hardv2_route_gate`
- `hardv2_gate`
- `Saved-link handoff`
- `Lookup handoff`
- `Control handoff`
- `Label workspace gateway`

## Template Targets Likely Needed

The following clean templates are the main hardv3 source targets:

| Behavior area | Clean template path |
|---|---|
| Bookmark list and search | `/etc/linkding/bookmarks/templates/bookmarks/bookmark_page.html` |
| Bookmark rows/list partials | `/etc/linkding/bookmarks/templates/bookmarks/bookmark_list.html` |
| Bulk edit controls | `/etc/linkding/bookmarks/templates/bookmarks/bulk_edit_bar.html` |
| Add/edit bookmark forms | `/etc/linkding/bookmarks/templates/bookmarks/new.html`, `/etc/linkding/bookmarks/templates/bookmarks/form.html`, `/etc/linkding/bookmarks/templates/bookmarks/edit.html` |
| Login surface | `/etc/linkding/bookmarks/templates/registration/login.html` |
| Settings | `/etc/linkding/bookmarks/templates/settings/general.html`, `/etc/linkding/bookmarks/templates/settings/integrations.html`, `/etc/linkding/bookmarks/templates/settings/create_api_token_modal.html` |
| Shared layout/nav | `/etc/linkding/bookmarks/templates/shared/layout.html`, `/etc/linkding/bookmarks/templates/shared/head.html`, `/etc/linkding/bookmarks/templates/shared/nav_menu.html`, `/etc/linkding/bookmarks/templates/shared/top_frame.html` |
| Tags/labels | `/etc/linkding/bookmarks/templates/tags/index.html`, `/etc/linkding/bookmarks/templates/tags/form.html`, `/etc/linkding/bookmarks/templates/tags/new.html`, `/etc/linkding/bookmarks/templates/tags/edit.html`, `/etc/linkding/bookmarks/templates/tags/merge.html` |

## Validation Commands

Module state used for baseline inspection:

```bash
module load singularity/4.3.4
source scripts/singularity/linkding_runtime_lib.sh
image="$(image_path_for_version 1.45.0)"
sha256sum "$image"
singularity exec "$image" /bin/sh -lc "find /etc/linkding/bookmarks/templates -type f | sort" > /tmp/linkding_1450_templates_hardv3_baseline.txt
wc -l /tmp/linkding_1450_templates_hardv3_baseline.txt
```

Before hardv3 website validation, run a guard like:

```bash
! rg -n "hardv2_route_gate|hardv2_gate|Saved-link handoff|Lookup handoff|Control handoff|Label workspace gateway" \
  scripts/singularity/linkding_drift/variants/common \
  scripts/singularity/linkding_drift/variants/access \
  scripts/singularity/linkding_drift/variants/surface \
  scripts/singularity/linkding_drift/variants/content \
  scripts/singularity/linkding_drift/variants/runtime \
  scripts/singularity/linkding_drift/variants/process \
  scripts/singularity/linkding_drift/variants/structural \
  scripts/singularity/linkding_drift/variants/functional
```
