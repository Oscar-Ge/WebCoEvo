#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VARIANT_ROOT = ROOT / "scripts" / "singularity" / "linkding_drift" / "variants"
FIRST_MODIFIED_ROOT = ROOT / "websites" / "first_modified" / "variant_templates"
LINKDING_DRIFT_VERSION = "1.45.0"
CONTROL_VARIANT = "control"
LINKDING_DRIFT_PROFILE = (
    os.environ.get("LINKDING_DRIFT_PROFILE", "hardv3").strip().lower() or "hardv3"
)


def _variant_file(variant: str, relative_path: str) -> str:
    return str(VARIANT_ROOT / variant / relative_path)


def _first_modified_file(variant: str, relative_path: str) -> str:
    return str(FIRST_MODIFIED_ROOT / variant / relative_path)


def _bind(variant: str, relative_path: str, target: str) -> dict:
    return {
        "source": _variant_file(variant, relative_path),
        "target": target,
    }


def _first_modified_bind(variant: str, relative_path: str, target: str) -> dict:
    return {
        "source": _first_modified_file(variant, relative_path),
        "target": target,
    }


FIRST_MODIFIED_BINDS = {
    "access": [
        _first_modified_bind(
            "access",
            "templates/registration/login.html",
            "/etc/linkding/bookmarks/templates/registration/login.html",
        )
    ],
    "surface": [
        _first_modified_bind(
            "surface",
            "templates/shared/layout.html",
            "/etc/linkding/bookmarks/templates/shared/layout.html",
        )
    ],
    "content": [
        _first_modified_bind(
            "content",
            "templates/shared/nav_menu.html",
            "/etc/linkding/bookmarks/templates/shared/nav_menu.html",
        ),
        _first_modified_bind(
            "content",
            "templates/tags/index.html",
            "/etc/linkding/bookmarks/templates/tags/index.html",
        ),
    ],
    "structural": [
        _first_modified_bind(
            "structural",
            "templates/shared/nav_menu.html",
            "/etc/linkding/bookmarks/templates/shared/nav_menu.html",
        )
    ],
    "functional": [
        _first_modified_bind(
            "functional",
            "templates/bookmarks/bookmark_page.html",
            "/etc/linkding/bookmarks/templates/bookmarks/bookmark_page.html",
        )
    ],
    "process": [
        _first_modified_bind(
            "process",
            "templates/bookmarks/new.html",
            "/etc/linkding/bookmarks/templates/bookmarks/new.html",
        )
    ],
    "runtime": [
        _first_modified_bind(
            "runtime",
            "templates/shared/layout.html",
            "/etc/linkding/bookmarks/templates/shared/layout.html",
        )
    ],
}


FIRST_MODIFIED_SMOKE = {
    "access": {
        "path_assertions": [
            {
                "path": "/login",
                "requires_auth": False,
                "must_include": ["stepped sign-in flow", "Username", "Continue"],
                "must_not_include": [],
            }
        ]
    },
    "surface": {
        "path_assertions": [
            {
                "path": "/bookmarks",
                "requires_auth": True,
                "must_include": ["Visual refresh active"],
                "must_not_include": [],
            }
        ]
    },
    "content": {
        "path_assertions": [
            {
                "path": "/tags",
                "requires_auth": True,
                "must_include": ["Labels", "Create Label"],
                "must_not_include": [],
            }
        ]
    },
    "structural": {
        "path_assertions": [
            {
                "path": "/bookmarks",
                "requires_auth": True,
                "must_include": ["Collections", "Settings"],
                "must_not_include": [],
            }
        ]
    },
    "functional": {
        "path_assertions": [
            {
                "path": "/bookmarks",
                "requires_auth": True,
                "must_include": ["Feature-limited mode"],
                "must_not_include": [],
            }
        ]
    },
    "process": {
        "path_assertions": [
            {
                "path": "/bookmarks/new",
                "requires_auth": True,
                "must_include": ["Review new bookmark", "Step 1 of 2"],
                "must_not_include": [],
            }
        ]
    },
    "runtime": {
        "path_assertions": [
            {
                "path": "/bookmarks",
                "requires_auth": True,
                "must_include": ["Delayed rendering active"],
                "must_not_include": [],
            }
        ]
    },
}


def _hardv2_common_binds() -> list:
    return [
        _bind(
            "common",
            "templates/shared/hardv2_route_gate_head.html",
            "/etc/linkding/bookmarks/templates/shared/hardv2_route_gate_head.html",
        ),
        _bind(
            "common",
            "templates/shared/hardv2_route_gate_body.html",
            "/etc/linkding/bookmarks/templates/shared/hardv2_route_gate_body.html",
        ),
    ]


def _hardv2_layout_binds(variant: str) -> list:
    return [
        _bind(
            variant,
            "templates/shared/layout.html",
            "/etc/linkding/bookmarks/templates/shared/layout.html",
        )
    ] + _hardv2_common_binds()


def _hardv3_common_binds() -> list:
    return [
        _bind(
            "common",
            "templates/shared/hardv3_release_grounded_head.html",
            "/etc/linkding/bookmarks/templates/shared/hardv3_release_grounded_head.html",
        ),
        _bind(
            "common",
            "templates/shared/hardv3_release_grounded_body.html",
            "/etc/linkding/bookmarks/templates/shared/hardv3_release_grounded_body.html",
        ),
    ]


def _hardv3_layout_binds(variant: str) -> list:
    return [
        _bind(
            variant,
            "templates/shared/layout.html",
            "/etc/linkding/bookmarks/templates/shared/layout.html",
        )
    ] + _hardv3_common_binds()


def _seed_variant_row(
    *,
    variant,
    port,
    note,
    risk,
    bind_mounts,
    smoke,
    seed_anchor_task_id,
    hardness_focus,
    approximation=False,
):
    return {
        "port": port,
        "note": note,
        "risk": risk,
        "approximation": approximation,
        "bind_mounts": bind_mounts,
        "env": {},
        "seed_anchor_task_id": seed_anchor_task_id,
        "hardness_focus": list(hardness_focus),
        "smoke": smoke,
    }


LINKDING_DRIFT_VARIANTS = {
    "control": {
        "port": 9099,
        "note": "Unmodified control profile on Linkding 1.45.0.",
        "risk": "low",
        "approximation": False,
        "bind_mounts": [],
        "env": {},
        "smoke": {
            "path_assertions": [
                {
                    "path": "/login",
                    "requires_auth": False,
                    "must_include": ["Login", "Username", "Password"],
                    "must_not_include": [],
                }
            ]
        },
    },
    "surface": {
        "port": 9100,
        "note": "Release-grounded surface drift with row-scoped list controls and staged bookmark intake.",
        "risk": "medium",
        "approximation": False,
        "bind_mounts": _hardv3_layout_binds("surface"),
        "env": {},
        "smoke": {
            "path_assertions": [
                {
                    "path": "/bookmarks",
                    "requires_auth": True,
                    "must_include": ["hardv3-release-grounded", "Release list controls", "Select a row to enable actions"],
                    "must_not_include": [],
                }
            ]
        },
    },
    "structural": {
        "port": 9101,
        "note": "Release-grounded structural drift with settings subpanel and tag dialog indirection.",
        "risk": "medium",
        "approximation": False,
        "bind_mounts": _hardv3_layout_binds("structural") + [
            {
                "source": _variant_file("structural", "templates/shared/nav_menu.html"),
                "target": "/etc/linkding/bookmarks/templates/shared/nav_menu.html",
            }
        ],
        "env": {},
        "smoke": {
            "path_assertions": [
                {
                    "path": "/settings",
                    "requires_auth": True,
                    "must_include": ["hardv3-release-grounded", "Release control hub", "Security and integrations"],
                    "must_not_include": [],
                }
            ]
        },
    },
    "functional": {
        "port": 9102,
        "note": "Release-grounded functional drift with query-chip apply and settings subpanel routing.",
        "risk": "medium",
        "approximation": False,
        "bind_mounts": _hardv3_layout_binds("functional"),
        "env": {},
        "smoke": {
            "path_assertions": [
                {
                    "path": "/bookmarks?q=focus20-route-filter",
                    "requires_auth": True,
                    "must_include": ["hardv3-release-grounded", "Release lookup chip", "Apply lookup chip"],
                    "must_not_include": [],
                }
            ]
        },
    },
    "access": {
        "port": 9103,
        "note": "Release-grounded access drift based on login availability and local-credential fallback.",
        "risk": "high",
        "approximation": True,
        "bind_mounts": _hardv3_layout_binds("access") + [
            {
                "source": _variant_file("access", "templates/registration/login.html"),
                "target": "/etc/linkding/bookmarks/templates/registration/login.html",
            }
        ],
        "env": {},
        "smoke": {
            "path_assertions": [
                {
                    "path": "/login",
                    "requires_auth": False,
                    "must_include": ["hardv3-release-grounded", "Release access mode", "Use local credentials", "Username", "Password"],
                    "must_not_include": [],
                }
            ]
        },
    },
    "content": {
        "port": 9104,
        "note": "Release-grounded content drift with label wording and staged lookup chips.",
        "risk": "medium",
        "approximation": False,
        "bind_mounts": _hardv3_layout_binds("content") + [
            {
                "source": _variant_file("content", "templates/shared/nav_menu.html"),
                "target": "/etc/linkding/bookmarks/templates/shared/nav_menu.html",
            },
            {
                "source": _variant_file("content", "templates/tags/index.html"),
                "target": "/etc/linkding/bookmarks/templates/tags/index.html",
            },
        ],
        "env": {},
        "smoke": {
            "path_assertions": [
                {
                    "path": "/bookmarks?q=focus20-route-filter",
                    "requires_auth": True,
                    "must_include": ["hardv3-release-grounded", "Release lookup chip", "Apply lookup chip"],
                    "must_not_include": [],
                }
            ]
        },
    },
    "process": {
        "port": 9105,
        "note": "Release-grounded process drift with workflow checkpoints, tag dialog flow, and settings subpanels.",
        "risk": "high",
        "approximation": True,
        "bind_mounts": _hardv3_layout_binds("process"),
        "env": {},
        "smoke": {
            "path_assertions": [
                {
                    "path": "/bookmarks/new",
                    "requires_auth": True,
                    "must_include": ["hardv3-release-grounded", "Release workflow checkpoint", "Open release dialog"],
                    "must_not_include": [],
                }
            ]
        },
    },
    "runtime": {
        "port": 9106,
        "note": "Release-grounded runtime drift with readiness-gated row and bookmark-form controls.",
        "risk": "high",
        "approximation": True,
        "bind_mounts": _hardv3_layout_binds("runtime"),
        "env": {},
        "smoke": {
            "path_assertions": [
                {
                    "path": "/bookmarks",
                    "requires_auth": True,
                    "must_include": ["hardv3-release-grounded", "Release readiness mode", "Workspace controls are syncing"],
                    "must_not_include": [],
                }
            ]
        },
    },
    "surface_16005": {
        "port": 9107,
        "note": "Task-targeted surface drift for AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS.",
        "risk": "medium",
        "approximation": False,
        "bind_mounts": [
            {
                "source": _variant_file(
                    "surface_16005", "templates/bookmarks/new.html"
                ),
                "target": "/etc/linkding/bookmarks/templates/bookmarks/new.html",
            }
        ],
        "env": {},
        "smoke": {
            "path_assertions": [
                {
                    "path": "/bookmarks/new",
                    "requires_auth": True,
                    "must_include": ["Draft capture", "Review details"],
                    "must_not_include": [],
                }
            ]
        },
    },
    "runtime_16005": {
        "port": 9108,
        "note": "Task-targeted runtime drift for AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS.",
        "risk": "high",
        "approximation": False,
        "bind_mounts": [
            {
                "source": _variant_file(
                    "runtime_16005", "templates/bookmarks/new.html"
                ),
                "target": "/etc/linkding/bookmarks/templates/bookmarks/new.html",
            }
        ],
        "env": {},
        "smoke": {
            "path_assertions": [
                {
                    "path": "/bookmarks/new",
                    "requires_auth": True,
                    "must_include": ["Preparing saved view", "Review details"],
                    "must_not_include": [],
                }
            ],
            "browser_assertions": [
                {
                    "path": "/bookmarks/new",
                    "requires_auth": True,
                    "visible_selectors": [
                        "#runtime-prefill-shell:not(.runtime-hidden)",
                        "#runtime-prefill-ready:not(.runtime-hidden)",
                    ],
                    "enabled_selectors": [
                        "#runtime-prefill-shell input[type='submit']:not([disabled])",
                    ],
                    "must_include_text": ["Action area is now ready."],
                    "must_not_include_text": [],
                }
            ],
        },
    },
    "surface_16016": {
        "port": 9109,
        "note": "Task-targeted surface drift for AF20_ROUTE_TAGS_TO_SETTINGS.",
        "risk": "medium",
        "approximation": False,
        "bind_mounts": [
            {
                "source": _variant_file(
                    "surface_16016", "templates/shared/nav_menu.html"
                ),
                "target": "/etc/linkding/bookmarks/templates/shared/nav_menu.html",
            },
            {
                "source": _variant_file("surface_16016", "templates/tags/index.html"),
                "target": "/etc/linkding/bookmarks/templates/tags/index.html",
            },
        ],
        "env": {},
        "smoke": {
            "path_assertions": [
                {
                    "path": "/tags",
                    "requires_auth": True,
                    "must_include": ["Tag workspace", "Workspace navigation"],
                    "must_not_include": [],
                }
            ],
            "navigation_assertions": [
                {
                    "start_path": "/tags",
                    "requires_auth": True,
                    "open_button_text": "Workspace navigation",
                    "link_text": "Settings",
                    "target_path_contains": "/settings",
                    "target_must_include": ["Settings", "Profile"],
                    "target_must_not_include": [],
                }
            ],
        },
    },
}

LINKDING_DRIFT_VARIANTS.update(
    {
        "surface_16005": _seed_variant_row(
            variant="surface_16005",
            port=9107,
            note="Task-targeted surface drift for AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS.",
            risk="medium",
            bind_mounts=[
                _bind(
                    "surface_16005",
                    "templates/bookmarks/new.html",
                    "/etc/linkding/bookmarks/templates/bookmarks/new.html",
                )
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/bookmarks/new",
                        "requires_auth": True,
                        "must_include": ["Draft capture", "Review details"],
                        "must_not_include": [],
                    }
                ]
            },
            seed_anchor_task_id=16005,
            hardness_focus=["surface", "prefilled_form_reframing"],
        ),
        "runtime_16005": _seed_variant_row(
            variant="runtime_16005",
            port=9108,
            note="Task-targeted runtime drift for AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS.",
            risk="high",
            bind_mounts=[
                _bind(
                    "runtime_16005",
                    "templates/bookmarks/new.html",
                    "/etc/linkding/bookmarks/templates/bookmarks/new.html",
                )
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/bookmarks/new",
                        "requires_auth": True,
                        "must_include": ["Preparing saved view", "Review details"],
                        "must_not_include": [],
                    }
                ],
                "browser_assertions": [
                    {
                        "path": "/bookmarks/new",
                        "requires_auth": True,
                        "visible_selectors": [
                            "#runtime-prefill-shell:not(.runtime-hidden)",
                            "#runtime-prefill-ready:not(.runtime-hidden)",
                        ],
                        "enabled_selectors": [
                            "#runtime-prefill-shell input[type='submit']:not([disabled])",
                        ],
                        "must_include_text": ["Action area is now ready."],
                        "must_not_include_text": [],
                    }
                ],
            },
            seed_anchor_task_id=16005,
            hardness_focus=["runtime", "staged_ready_signal"],
        ),
        "surface_16016": _seed_variant_row(
            variant="surface_16016",
            port=9109,
            note="Task-targeted surface drift for AF20_ROUTE_TAGS_TO_SETTINGS.",
            risk="medium",
            bind_mounts=[
                _bind(
                    "surface_16016",
                    "templates/shared/nav_menu.html",
                    "/etc/linkding/bookmarks/templates/shared/nav_menu.html",
                ),
                _bind(
                    "surface_16016",
                    "templates/tags/index.html",
                    "/etc/linkding/bookmarks/templates/tags/index.html",
                ),
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/tags",
                        "requires_auth": True,
                        "must_include": ["Tag workspace", "Workspace navigation"],
                        "must_not_include": [],
                    }
                ],
                "navigation_assertions": [
                    {
                        "start_path": "/tags",
                        "requires_auth": True,
                        "open_button_text": "Workspace navigation",
                        "link_text": "Settings",
                        "target_path_contains": "/settings",
                        "target_must_include": ["Settings", "Profile"],
                        "target_must_not_include": [],
                    }
                ],
            },
            seed_anchor_task_id=16016,
            hardness_focus=["surface", "navigation_relabeling"],
        ),
        "process_16005": _seed_variant_row(
            variant="process_16005",
            port=9110,
            note="Task-targeted process drift for AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS.",
            risk="high",
            bind_mounts=[
                _bind(
                    "process_16005",
                    "templates/bookmarks/new.html",
                    "/etc/linkding/bookmarks/templates/bookmarks/new.html",
                )
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/bookmarks/new",
                        "requires_auth": True,
                        "must_include": ["Review sequence", "Continue after review"],
                        "must_not_include": [],
                    }
                ]
            },
            seed_anchor_task_id=16005,
            hardness_focus=["process", "extra_review_step"],
        ),
        "content_16005": _seed_variant_row(
            variant="content_16005",
            port=9111,
            note="Task-targeted content drift for AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS.",
            risk="medium",
            bind_mounts=[
                _bind(
                    "content_16005",
                    "templates/bookmarks/new.html",
                    "/etc/linkding/bookmarks/templates/bookmarks/new.html",
                )
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/bookmarks/new",
                        "requires_auth": True,
                        "must_include": ["Saved page draft", "Filing labels"],
                        "must_not_include": [],
                    }
                ]
            },
            seed_anchor_task_id=16005,
            hardness_focus=["content", "bookmark_vocab_shift"],
        ),
        "structural_16016": _seed_variant_row(
            variant="structural_16016",
            port=9112,
            note="Task-targeted structural drift for AF20_ROUTE_TAGS_TO_SETTINGS.",
            risk="medium",
            bind_mounts=[
                _bind(
                    "structural_16016",
                    "templates/shared/nav_menu.html",
                    "/etc/linkding/bookmarks/templates/shared/nav_menu.html",
                ),
                _bind(
                    "structural_16016",
                    "templates/tags/index.html",
                    "/etc/linkding/bookmarks/templates/tags/index.html",
                ),
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/tags",
                        "requires_auth": True,
                        "must_include": ["Workspace map", "Settings shelf"],
                        "must_not_include": [],
                    }
                ],
                "navigation_assertions": [
                    {
                        "start_path": "/tags",
                        "requires_auth": True,
                        "open_button_text": "Workspace map",
                        "link_text": "Settings shelf",
                        "target_path_contains": "/settings",
                        "target_must_include": ["Settings", "Profile"],
                        "target_must_not_include": [],
                    }
                ],
            },
            seed_anchor_task_id=16016,
            hardness_focus=["structural", "navigation_regrouping"],
        ),
        "functional_16016": _seed_variant_row(
            variant="functional_16016",
            port=9113,
            note="Task-targeted functional drift for AF20_ROUTE_TAGS_TO_SETTINGS.",
            risk="medium",
            bind_mounts=[
                _bind(
                    "functional_16016",
                    "templates/shared/nav_menu.html",
                    "/etc/linkding/bookmarks/templates/shared/nav_menu.html",
                ),
                _bind(
                    "functional_16016",
                    "templates/tags/index.html",
                    "/etc/linkding/bookmarks/templates/tags/index.html",
                ),
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/tags",
                        "requires_auth": True,
                        "must_include": ["Workspace tools", "Preferences"],
                        "must_not_include": [],
                    }
                ],
                "navigation_assertions": [
                    {
                        "start_path": "/tags",
                        "requires_auth": True,
                        "open_button_text": "Workspace tools",
                        "link_text": "Preferences",
                        "target_path_contains": "/settings",
                        "target_must_include": ["Settings", "Profile"],
                        "target_must_not_include": [],
                    }
                ],
            },
            seed_anchor_task_id=16016,
            hardness_focus=["functional", "settings_grouping_shift"],
        ),
        "access_9738": _seed_variant_row(
            variant="access_9738",
            port=9114,
            note="Task-targeted access drift for AF20_ANCHOR_LOGIN_BOOKMARK_FORM.",
            risk="high",
            bind_mounts=[
                _bind(
                    "access_9738",
                    "templates/registration/login.html",
                    "/etc/linkding/bookmarks/templates/registration/login.html",
                )
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/login",
                        "requires_auth": False,
                        "must_include": ["Account access", "Destination sign-in"],
                        "must_not_include": [],
                    }
                ]
            },
            seed_anchor_task_id=9738,
            hardness_focus=["access", "login_surface_shift"],
            approximation=True,
        ),
        "process_9738": _seed_variant_row(
            variant="process_9738",
            port=9115,
            note="Task-targeted process drift for AF20_ANCHOR_LOGIN_BOOKMARK_FORM.",
            risk="high",
            bind_mounts=[
                _bind(
                    "process_9738",
                    "templates/bookmarks/new.html",
                    "/etc/linkding/bookmarks/templates/bookmarks/new.html",
                )
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/bookmarks/new",
                        "requires_auth": True,
                        "must_include": ["Continue to destination", "Bookmark intake"],
                        "must_not_include": [],
                    }
                ]
            },
            seed_anchor_task_id=9738,
            hardness_focus=["process", "post_login_intermediate_step"],
        ),
        "runtime_9738": _seed_variant_row(
            variant="runtime_9738",
            port=9116,
            note="Task-targeted runtime drift for AF20_ANCHOR_LOGIN_BOOKMARK_FORM.",
            risk="high",
            bind_mounts=[
                _bind(
                    "runtime_9738",
                    "templates/bookmarks/new.html",
                    "/etc/linkding/bookmarks/templates/bookmarks/new.html",
                )
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/bookmarks/new",
                        "requires_auth": True,
                        "must_include": ["Preparing destination", "Bookmark intake"],
                        "must_not_include": [],
                    }
                ],
                "browser_assertions": [
                    {
                        "path": "/bookmarks/new",
                        "requires_auth": True,
                        "visible_selectors": [
                            "#runtime-destination-shell:not(.runtime-hidden)",
                            "#runtime-destination-ready:not(.runtime-hidden)",
                        ],
                        "enabled_selectors": [
                            "#runtime-destination-shell input[type='submit']:not([disabled])",
                        ],
                        "must_include_text": ["Destination is ready."],
                        "must_not_include_text": [],
                    }
                ],
            },
            seed_anchor_task_id=9738,
            hardness_focus=["runtime", "redirect_ready_delay"],
        ),
        "access_9730": _seed_variant_row(
            variant="access_9730",
            port=9117,
            note="Task-targeted access drift for AF20_ANCHOR_LOGIN_HOME.",
            risk="high",
            bind_mounts=[
                _bind(
                    "access_9730",
                    "templates/registration/login.html",
                    "/etc/linkding/bookmarks/templates/registration/login.html",
                )
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/login",
                        "requires_auth": False,
                        "must_include": ["Account access", "Workspace sign-in"],
                        "must_not_include": [],
                    }
                ]
            },
            seed_anchor_task_id=9730,
            hardness_focus=["access", "home_login_relabeling"],
            approximation=True,
        ),
        "content_9730": _seed_variant_row(
            variant="content_9730",
            port=9118,
            note="Task-targeted content drift for AF20_ANCHOR_LOGIN_HOME.",
            risk="medium",
            bind_mounts=[
                _bind(
                    "content_9730",
                    "templates/bookmarks/bookmark_page.html",
                    "/etc/linkding/bookmarks/templates/bookmarks/bookmark_page.html",
                )
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/bookmarks",
                        "requires_auth": True,
                        "must_include": ["Saved pages", "Capture filters"],
                        "must_not_include": [],
                    }
                ]
            },
            seed_anchor_task_id=9730,
            hardness_focus=["content", "bookmarks_home_vocab_shift"],
        ),
        "surface_9704": _seed_variant_row(
            variant="surface_9704",
            port=9119,
            note="Task-targeted surface drift for AF20_ANCHOR_OPEN_BOOKMARK_FORM.",
            risk="medium",
            bind_mounts=[
                _bind(
                    "surface_9704",
                    "templates/bookmarks/bookmark_page.html",
                    "/etc/linkding/bookmarks/templates/bookmarks/bookmark_page.html",
                )
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/bookmarks",
                        "requires_auth": True,
                        "must_include": ["Capture actions", "Open draft"],
                        "must_not_include": [],
                    }
                ]
            },
            seed_anchor_task_id=9704,
            hardness_focus=["surface", "entry_button_relabeling"],
        ),
        "structural_9704": _seed_variant_row(
            variant="structural_9704",
            port=9120,
            note="Task-targeted structural drift for AF20_ANCHOR_OPEN_BOOKMARK_FORM.",
            risk="medium",
            bind_mounts=[
                _bind(
                    "structural_9704",
                    "templates/bookmarks/bookmark_page.html",
                    "/etc/linkding/bookmarks/templates/bookmarks/bookmark_page.html",
                )
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/bookmarks",
                        "requires_auth": True,
                        "must_include": ["Bookmark workspace", "Capture rail"],
                        "must_not_include": [],
                    }
                ]
            },
            seed_anchor_task_id=9704,
            hardness_focus=["structural", "entry_control_repositioning"],
        ),
        "runtime_9704": _seed_variant_row(
            variant="runtime_9704",
            port=9121,
            note="Task-targeted runtime drift for AF20_ANCHOR_OPEN_BOOKMARK_FORM.",
            risk="high",
            bind_mounts=[
                _bind(
                    "runtime_9704",
                    "templates/bookmarks/bookmark_page.html",
                    "/etc/linkding/bookmarks/templates/bookmarks/bookmark_page.html",
                )
            ],
            smoke={
                "path_assertions": [
                    {
                        "path": "/bookmarks",
                        "requires_auth": True,
                        "must_include": ["Preparing capture workspace", "Open draft"],
                        "must_not_include": [],
                    }
                ],
                "browser_assertions": [
                    {
                        "path": "/bookmarks",
                        "requires_auth": True,
                        "visible_selectors": [
                            "#runtime-capture-trigger:not([disabled])",
                        ],
                        "enabled_selectors": [
                            "#runtime-capture-trigger:not([disabled])",
                        ],
                        "must_include_text": ["Capture controls are ready."],
                        "must_not_include_text": [],
                    }
                ],
            },
            seed_anchor_task_id=9704,
            hardness_focus=["runtime", "entry_control_ready_delay"],
        ),
    }
)


def _apply_control_profile() -> None:
    for name, row in LINKDING_DRIFT_VARIANTS.items():
        row["bind_mounts"] = []
        row["env"] = {}
        if name != CONTROL_VARIANT:
            row["note"] = (
                "Unmodified control profile on Linkding 1.45.0; "
                f"task metadata keeps the {name} drift label."
            )
            row["smoke"] = LINKDING_DRIFT_VARIANTS[CONTROL_VARIANT]["smoke"]


def _apply_first_modified_profile() -> None:
    for name, row in LINKDING_DRIFT_VARIANTS.items():
        row["env"] = {}
        if name == CONTROL_VARIANT:
            row["bind_mounts"] = []
            row["note"] = "Unmodified control profile on Linkding 1.45.0."
            continue
        if name in FIRST_MODIFIED_BINDS:
            row["bind_mounts"] = FIRST_MODIFIED_BINDS[name]
            row["note"] = (
                "First-modified historical drift profile restored from "
                f"websites/first_modified/variant_templates/{name}."
            )
            row["smoke"] = FIRST_MODIFIED_SMOKE[name]
        else:
            # The first-modified snapshot only contains the seven base drifts.
            row["bind_mounts"] = []
            row["note"] = (
                "First-modified profile has no task-targeted override for "
                f"{name}; this variant falls back to the clean runtime."
            )
            row["smoke"] = LINKDING_DRIFT_VARIANTS[CONTROL_VARIANT]["smoke"]


def _apply_profile() -> None:
    if LINKDING_DRIFT_PROFILE == "hardv3":
        return
    if LINKDING_DRIFT_PROFILE == "control":
        _apply_control_profile()
        return
    if LINKDING_DRIFT_PROFILE == "first_modified":
        _apply_first_modified_profile()
        return
    raise ValueError(
        "unknown LINKDING_DRIFT_PROFILE="
        f"{LINKDING_DRIFT_PROFILE}; expected hardv3, first_modified, or control"
    )


_apply_profile()


def iter_variants():
    return LINKDING_DRIFT_VARIANTS.items()


def get_variant(name: str) -> dict:
    try:
        return LINKDING_DRIFT_VARIANTS[name]
    except KeyError as exc:
        raise KeyError(f"unknown drift variant: {name}") from exc


def build_static_summary() -> dict:
    high_risk_variants = [
        name for name, row in iter_variants() if row["risk"] == "high"
    ]
    seed_variants = [
        name for name, row in iter_variants() if int(row.get("seed_anchor_task_id", 0)) > 0
    ]
    seed_family_counts = {}
    for name in seed_variants:
        family_id = str(get_variant(name)["seed_anchor_task_id"])
        seed_family_counts[family_id] = seed_family_counts.get(family_id, 0) + 1
    return {
        "version": LINKDING_DRIFT_VERSION,
        "variant_count": len(LINKDING_DRIFT_VARIANTS),
        "ports": {name: row["port"] for name, row in iter_variants()},
        "high_risk_variants": high_risk_variants,
        "approximated_variants": [
            name for name, row in iter_variants() if row["approximation"]
        ],
        "bind_mount_counts": {
            name: len(row["bind_mounts"]) for name, row in iter_variants()
        },
        "seed_variants": seed_variants,
        "seed_variant_count": len(seed_variants),
        "seed_family_counts": dict(
            sorted(seed_family_counts.items(), key=lambda item: int(item[0]))
        ),
    }


def render_summary_text() -> str:
    summary = build_static_summary()
    lines = [
        f"Linkding drift version: {summary['version']}",
        f"Variant count: {summary['variant_count']}",
        "Ports:",
    ]
    for name, port in summary["ports"].items():
        lines.append(f"- {name}: {port}")
    lines.append("High-risk variants: " + ", ".join(summary["high_risk_variants"]))
    lines.append(
        "Approximated variants: " + ", ".join(summary["approximated_variants"])
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant")
    parser.add_argument(
        "--format",
        default="summary",
        choices=["summary", "json", "names", "binds", "env", "static-summary"],
    )
    parser.add_argument("--field")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.variant:
        row = get_variant(args.variant)
        if args.field:
            value = row[args.field]
            if isinstance(value, (dict, list)):
                print(json.dumps(value, ensure_ascii=True))
            else:
                print(value)
            return 0
        if args.format == "json":
            print(json.dumps(row, ensure_ascii=True, indent=2))
            return 0
        if args.format == "binds":
            for bind in row["bind_mounts"]:
                print(f"{bind['source']}\t{bind['target']}")
            return 0
        if args.format == "env":
            for key, value in row["env"].items():
                print(f"{key}\t{value}")
            return 0

    if args.format == "names":
        for name in LINKDING_DRIFT_VARIANTS:
            print(name)
        return 0
    if args.format == "json":
        print(json.dumps(LINKDING_DRIFT_VARIANTS, ensure_ascii=True, indent=2))
        return 0
    if args.format == "static-summary":
        print(json.dumps(build_static_summary(), ensure_ascii=True, indent=2))
        return 0

    print(render_summary_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
