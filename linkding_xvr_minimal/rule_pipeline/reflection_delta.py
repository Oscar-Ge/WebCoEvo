"""Build small delta evaluation slices from matched reflection transitions."""

import copy


TRANSITION_BUCKETS = [
    ("saved", "must_keep"),
    ("lost", "must_recover"),
    ("both_success", "regression_rails"),
    ("both_fail", "diagnostic_frontier"),
]


def select_delta_rows(transition_artifact, max_per_bucket=8):
    rows = [
        row
        for row in list((transition_artifact or {}).get("rows") or [])
        if str(row.get("validity") or "valid_for_mining") == "valid_for_mining"
    ]
    buckets = {}
    for transition, bucket_name in TRANSITION_BUCKETS:
        matching = [
            int(row.get("task_id") or 0)
            for row in sorted(rows, key=lambda item: int(item.get("task_id") or 0))
            if str(row.get("transition") or "") == transition and int(row.get("task_id") or 0)
        ]
        buckets[bucket_name] = matching[: int(max_per_bucket or 0)]
    selected_task_ids = []
    for _, bucket_name in TRANSITION_BUCKETS:
        for task_id in buckets[bucket_name]:
            if task_id not in selected_task_ids:
                selected_task_ids.append(task_id)
    return {
        "buckets": buckets,
        "selected_task_ids": selected_task_ids,
        "max_per_bucket": int(max_per_bucket or 0),
    }


def build_delta_task_file(task_rows, selected_ids):
    rows_by_id = {int(row.get("task_id") or 0): row for row in list(task_rows or [])}
    out = []
    for task_id in list(selected_ids or []):
        row = rows_by_id.get(int(task_id or 0))
        if row:
            out.append(copy.deepcopy(row))
    return out


def build_delta_manifest(selection, output_task_file="", max_per_bucket=8):
    buckets = dict((selection or {}).get("buckets") or {})
    return {
        "schema_version": "webcoevo-xvr-delta-slice-v1",
        "output_task_file": str(output_task_file or ""),
        "max_per_bucket": int(max_per_bucket or (selection or {}).get("max_per_bucket") or 0),
        "bucket_counts": {
            key: len(list(buckets.get(key) or []))
            for key in sorted([bucket for _, bucket in TRANSITION_BUCKETS])
        },
        "buckets": buckets,
        "selected_task_ids": list((selection or {}).get("selected_task_ids") or []),
    }
