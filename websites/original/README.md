# Original Linkding 1.45.0

This folder stores control-profile evidence for the unmodified Linkding `1.45.0` website.

## Contents

- `linkding_1_45_0_control_snapshots/_html/`: rendered HTML captures for representative control pages.
- `linkding_1_45_0_control_snapshots/*.png`: matching control screenshots.
- `docs/clean-baseline-source.md`: the clean-baseline note from the old research tree.

The actual runtime control profile is still defined by the empty `control` variant in `scripts/singularity/linkding_drift_manifest.py`: it uses the base Linkding image with no template bind mounts.

Captured HTML has local CSRF token values sanitized to `SANITIZED_CSRF_TOKEN`.
