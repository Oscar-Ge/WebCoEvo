# Linkding hardv3 Template Targets

**Date:** 2026-04-13  
**Purpose:** Pin hardv3 release-grounded website edits to clean Linkding `v1.45.0` template targets before implementation.

## Baseline Source

- Clean image: `/home/gecm/linkding-baselines/images/linkding_1450.sif`
- Image SHA256: `0571f0ccf47429bc4f2b87cc7ba55de2207a71661ce5e5122c0b757987d7a84c`
- Template root: `/etc/linkding/bookmarks/templates`
- Discovery command: `module load singularity/4.3.4 && find /etc/linkding/bookmarks/templates -type f | sort`

Hardv3 must start from these clean `v1.45.0` templates, not from the hardv2 route-gate layout.

## Primary Template Targets

| Operator | Clean target | Local override target | Evaluator evidence preserved after human path |
|---|---|---|---|
| shared hardv3 release frame | `/etc/linkding/bookmarks/templates/shared/layout.html` | `scripts/singularity/linkding_drift/variants/<variant>/templates/shared/layout.html` | Original page content remains inside `{% block content %}` |
| shared hardv3 styles/scripts | new include under `shared/` | `scripts/singularity/linkding_drift/variants/common/templates/shared/hardv3_release_grounded_head.html` and `..._body.html` | Original final states remain reachable through visible controls |
| `auth_surface_availability` | `/etc/linkding/bookmarks/templates/registration/login.html` | `scripts/singularity/linkding_drift/variants/access/templates/registration/login.html` | Login form, CSRF token, and `next` hidden field |
| `settings_security_subpanel` | `/etc/linkding/bookmarks/templates/settings/general.html`; `/etc/linkding/bookmarks/templates/settings/integrations.html` | shared hardv3 layout/common behavior | `Settings`, `Profile`, and settings form controls after reveal |
| `tag_dialog_flow` | `/etc/linkding/bookmarks/templates/tags/index.html`; `tags/new.html`; `tags/edit.html`; `tags/merge.html` | shared hardv3 layout/common behavior plus existing content nav where applicable | `Tags`, tag table, create/edit/merge links after reveal |
| `row_scoped_action_container` | `/etc/linkding/bookmarks/templates/bookmarks/bookmark_page.html`; `bookmarks/bookmark_list.html`; `bookmarks/bulk_edit_bar.html` | shared hardv3 layout/common behavior | Bookmark list and row action controls |
| `query_chip_apply_flow` | `/etc/linkding/bookmarks/templates/bookmarks/bookmark_page.html`; `bookmarks/search.html` | shared hardv3 layout/common behavior | Exact `focus20-*` query evidence after visible apply |
| `url_normalization_shift` | `/etc/linkding/bookmarks/templates/bookmarks/new.html`; `bookmarks/form.html` | shared hardv3 layout/common behavior | Existing bookmark form fields and prefilled values |

## Variant Binding Contract

The seven generic drift variants remain the experimental unit:

| Variant | Hardv3 composition | Required visible verifier cue |
|---|---|---|
| `access` | auth availability + auth option removal + post-login continuation | `Release access mode`; `Use local credentials` |
| `surface` | row-scoped actions + disabled-until-selection + stale first click | `Release list controls`; `Select a row to enable actions` |
| `content` | label wording + URL normalization + staged lookup chip | `Release language update`; `Apply lookup chip` |
| `runtime` | disabled-until-selection + stale first click + row-scoped actions | `Release readiness mode`; `Workspace controls are syncing` |
| `process` | tag dialog flow + post-login continuation + settings subpanel | `Release workflow checkpoint`; `Open release dialog` |
| `structural` | settings subpanel + tag dialog + label wording | `Release control hub`; `Security and integrations` |
| `functional` | query-chip apply + relative settings link + settings subpanel | `Release feature routing`; `Apply lookup chip` |

## Must Not Regress

- No generic hardv3 variant may bind `shared/hardv2_route_gate_head.html` or `shared/hardv2_route_gate_body.html`.
- The Focus20 task file and evaluator definitions remain unchanged.
- Every intermediate state must have a visible human path to the original final state.
- The smoke verifier should detect the hardv3 profile with `hardv3-release-grounded`.
