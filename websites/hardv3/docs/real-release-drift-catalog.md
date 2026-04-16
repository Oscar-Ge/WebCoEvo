# Linkding Real-Release Drift Catalog For hardv3

**Date:** 2026-04-13  
**Catalog:** `config_files/linkding_v1450_release_grounded_hardv3_operator_catalog_v1.json`  
**Purpose:** Convert real Linkding release/PR changes into hardv3 website-hardening operators controlled by the seven web version-shift taxonomy and tuned to the current `ExpeL + V2.4` capability boundary.

## Design Position

hardv3 should not copy GitHub PRs literally and should not inherit hardv2 route-gate code. Instead:

1. mine real Linkding version changes for plausible UI/workflow shifts;
2. map each shift to one or more taxonomy classes: `access`, `surface`, `content`, `runtime`, `process`, `structural`, `functional`;
3. compose `2-3` related pressures per clean-baseline website overlay;
4. tune composition intensity against V2.4 reflection-rule assumptions.

The primary task set remains unchanged:

- `config_files/linkding_v1450_focus20_website_probe_v1.raw.json`

## Release Sources

| Source | Release change | hardv3 operator |
|---|---|---|
| `https://github.com/sissbruecker/linkding/releases/tag/v1.45.0` | Linkding `v1.45.0` release notes | release-grounding pool |
| `https://github.com/sissbruecker/linkding/pull/1253` | Move tag management forms into dialogs | `tag_dialog_flow`, `content_label_wording_shift` |
| `https://github.com/sissbruecker/linkding/pull/1248` | API token management | `settings_security_subpanel` |
| `https://github.com/sissbruecker/linkding/pull/1261` | Remove absolute URIs from settings page | `settings_relative_link_shift` |
| `https://github.com/sissbruecker/linkding/pull/1269` | Add option to disable login form | `auth_surface_availability`, `post_login_continuation` |
| `https://github.com/sissbruecker/linkding/pull/1268` | Remove registration switch | `auth_option_removal` |
| `https://github.com/sissbruecker/linkding/pull/1257` | Move bulk edit checkboxes into bookmark list container | `row_scoped_action_container`, `query_chip_apply_flow` |
| `https://github.com/sissbruecker/linkding/pull/1241` | Disable bulk execute button when no bookmarks selected | `disabled_until_selection`, `stale_first_click_affordance` |
| `https://github.com/sissbruecker/linkding/pull/1225` | Turn scheme-less URLs into HTTPS instead of HTTP links | `url_normalization_shift` |

## Operator Table

| Operator | Drift classes | Main task families | V2.4 / ExpeL assumption attacked | hardv3 status |
|---|---|---|---|---|
| `tag_dialog_flow` | `structural`, `process`, `functional` | `16016`, tags navigation | Direct `/tags` route arrival is enough | selected |
| `settings_security_subpanel` | `structural`, `functional`, `process` | `16014`, `16016` | `/settings` URL/heading proves final state | selected |
| `settings_relative_link_shift` | `content`, `functional` | settings navigation | Remembered settings links remain stable | deferred as risky supporting pressure |
| `auth_surface_availability` | `access`, `process` | `16005`, login reentry | Login form is immediately visible | selected |
| `auth_option_removal` | `access`, `content` | login reentry | Auth page secondary affordances remain stable | selected |
| `row_scoped_action_container` | `surface`, `runtime`, `process` | `16013`, list actions | Remembered global controls remain valid | selected |
| `disabled_until_selection` | `runtime`, `surface` | `16013`, runtime readiness | Retrying stale click is enough | selected |
| `url_normalization_shift` | `content`, `functional` | `16005`, form prefill | Visible URL strings/defaults remain stable | selected with verifier risk gate |
| `query_chip_apply_flow` | `functional`, `process`, `content` | `16017`, filtered bookmarks | `/bookmarks?q=...` proves completion | selected |
| `content_label_wording_shift` | `content`, `surface` | `16016`, tags navigation | Literal old labels remain stable | selected |
| `post_login_continuation` | `access`, `process` | `16005`, login reentry | Login resumes directly to `next` target | selected |
| `stale_first_click_affordance` | `runtime`, `surface` | `16013`, runtime readiness | Blind retry handles early click failure | selected for frontier strengthening |

## Seven Website Compositions

Each hardv3 website starts from clean Linkding `v1.45.0` templates, has one primary taxonomy label, and composes related pressures.

| Website | Primary class | Composed pressures | Interpretation |
|---|---|---|---|
| `access` | `access` | `auth_surface_availability`, `auth_option_removal`, `post_login_continuation` | Auth-surface release evolution; attacks immediate-form and direct-`next` assumptions. |
| `surface` | `surface` | `row_scoped_action_container`, `disabled_until_selection`, `stale_first_click_affordance` | List action placement/readiness; attacks remembered global controls. |
| `content` | `content` | `content_label_wording_shift`, `url_normalization_shift`, `query_chip_apply_flow` | Wording/default/query evidence drift; attacks literal content matching. |
| `runtime` | `runtime` | `disabled_until_selection`, `stale_first_click_affordance`, `row_scoped_action_container` | Enabled-state and readiness drift; attacks stale-click retry. |
| `process` | `process` | `tag_dialog_flow`, `post_login_continuation`, `settings_security_subpanel` | Extra visible workflow steps; attacks one-click/one-route completion. |
| `structural` | `structural` | `settings_security_subpanel`, `tag_dialog_flow`, `content_label_wording_shift` | Hubs/dialogs/navigation relabeling; attacks direct-route and one-menu recovery. |
| `functional` | `functional` | `query_chip_apply_flow`, `settings_relative_link_shift`, `settings_security_subpanel` | Query/link/route semantics drift; attacks URL/query finalization. |

## Mapping To Current Evidence

Focus20 remains the primary test because the current claim is environment drift robustness with unchanged task semantics.

High-value anchors:

- `16005`: login redirect, prefill, tagged bookmark form, and process finalization.
- `16013`: stale-click and repeated-entry recovery.
- `16014`: settings navigation under hidden or misleading structure.
- `16016`: bookmarks/tags route-to-settings remapping.
- `16017`: filtered bookmark query completion.

Secondary checks:

- `TaskBank36 held-out`: checks whether release-grounded pressures remain meaningful beyond Focus20.
- `Website-adapted24`: checks whether the new sites expose an adversarial frontier rather than simply breaking rails.

## Recommendation

Proceed with the selected hardv3 operator subset, but keep two safeguards:

- Every operator must have a verifier path proving the original final evaluator state remains human-reachable.
- Every website should be reported as a composite release-grounded overlay, not as a pure single-factor taxonomy ablation.
