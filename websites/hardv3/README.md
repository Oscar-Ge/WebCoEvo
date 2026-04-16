# Hardv3 Release-Grounded Linkding Website

This folder stores the hardv3 release-grounded Linkding website generation used by WebCoEvo.

## Contents

- `variant_templates/`: archived copy of the active hardv3 template overrides.
- `report_v1/_html/`: rendered control and hardv3 validation HTML captures.
- `report_v1/*.png`: rendered control and hardv3 validation screenshots.
- `docs/`: hardv3 design notes copied from the old research tree.

The active runtime source remains:

```text
scripts/singularity/linkding_drift/variants/
```

Keep this archive in sync with runtime assets when changing hardv3 behavior. Captured HTML has local CSRF token values sanitized to `SANITIZED_CSRF_TOKEN`.
