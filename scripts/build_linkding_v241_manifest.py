#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


REQUIRED_FAMILIES = {
    "focus20": {
        "first_modified": {"v2_4": "focus20_first_modified_v2_4_expel_official_minimal_v1"},
        "hardv3": {"v2_4": "focus20_hardv3_v2_4_expel_official_minimal_v1"},
    },
    "taskbank36": {
        "first_modified": {"v2_4": "taskbank36_first_modified_v2_4_expel_official_minimal_v1"},
        "hardv3": {"v2_4": "taskbank36_hardv3_v2_4_expel_official_minimal_v1"},
    },
}

OPTIONAL_FAMILIES = {
    "focus20": {
        "first_modified": {"expel_only": "focus20_first_modified_expel_only_official_minimal_v1"},
        "hardv3": {"expel_only": "focus20_hardv3_expel_only_official_minimal_v1"},
    },
    "taskbank36": {
        "first_modified": {"expel_only": "taskbank36_first_modified_expel_only_official_minimal_v1"},
        "hardv3": {"expel_only": "taskbank36_hardv3_expel_only_official_minimal_v1"},
    },
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", required=True)
    parser.add_argument("--output-file", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    results_root = Path(args.results_root)
    manifest = {
        "schema_version": "webcoevo-linkding-v241-manifest-v1",
        "results_root": str(results_root.resolve()),
    }
    required_entries = 0
    optional_entries = 0
    summary = {}

    for dataset, variants in REQUIRED_FAMILIES.items():
        manifest[dataset] = {}
        summary[dataset] = {}
        for variant, labels in variants.items():
            manifest[dataset][variant] = {}
            summary[dataset][variant] = {}
            for label, family_name in labels.items():
                entry = resolve_family(results_root, family_name, required=True)
                manifest[dataset][variant][label] = entry
                summary[dataset][variant][label] = {"run_dir": entry["run_dirs"][0]}
                required_entries += 1

    for dataset, variants in OPTIONAL_FAMILIES.items():
        dataset_manifest = manifest.setdefault(dataset, {})
        dataset_summary = summary.setdefault(dataset, {})
        for variant, labels in variants.items():
            variant_manifest = dataset_manifest.setdefault(variant, {})
            variant_summary = dataset_summary.setdefault(variant, {})
            for label, family_name in labels.items():
                entry = resolve_family(results_root, family_name, required=False)
                if entry is None:
                    continue
                variant_manifest[label] = entry
                variant_summary[label] = {"run_dir": entry["run_dirs"][0]}
                optional_entries += 1

    manifest["required_entries"] = required_entries
    manifest["optional_entries"] = optional_entries

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    summary["required_entries"] = required_entries
    summary["optional_entries"] = optional_entries
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def resolve_family(results_root, family_name, required):
    family_root = Path(results_root) / family_name
    if not family_root.exists():
        if required:
            raise FileNotFoundError("Required result family is missing: {}".format(family_root))
        return None

    shard_dirs = sorted(
        path for path in family_root.iterdir() if path.is_dir() and path.name.startswith("shard_")
    )
    if not shard_dirs:
        shard_dirs = [family_root]

    run_dirs = []
    eval_paths = []
    trace_paths = []
    for shard_dir in shard_dirs:
        run_dir = select_run_dir(shard_dir)
        if run_dir is None:
            if required:
                raise FileNotFoundError("No usable run found under {}".format(shard_dir))
            continue
        eval_path = select_latest_file(run_dir, "uitars_eval_*.jsonl")
        trace_path = select_latest_file(run_dir, "uitars_trace_*.jsonl")
        if eval_path is None or trace_path is None:
            if required:
                raise FileNotFoundError("Missing eval/trace JSONL under {}".format(run_dir))
            continue
        run_dirs.append(str(run_dir))
        eval_paths.append(str(eval_path))
        trace_paths.append(str(trace_path))

    if not run_dirs:
        if required:
            raise FileNotFoundError("No usable eval/trace paths found for {}".format(family_root))
        return None

    entry = {
        "family_name": family_name,
        "family_root": str(family_root),
        "run_dir": derive_run_dir_value(family_root, run_dirs),
        "eval_path": derive_file_value(family_root, run_dirs, eval_paths, "uitars_eval_*.jsonl"),
        "trace_path": derive_file_value(family_root, run_dirs, trace_paths, "uitars_trace_*.jsonl"),
        "run_dirs": run_dirs,
        "eval_paths": eval_paths,
        "trace_paths": trace_paths,
    }
    return entry


def select_run_dir(shard_dir):
    candidates = []
    for path in sorted(path for path in Path(shard_dir).iterdir() if path.is_dir() and path.name.startswith("run_")):
        if select_latest_file(path, "uitars_eval_*.jsonl") and select_latest_file(path, "uitars_trace_*.jsonl"):
            candidates.append(path)
    if not candidates:
        return None
    candidates.sort(key=run_sort_key)
    return candidates[-1]


def run_sort_key(path):
    name = path.name.lower()
    return (
        1 if "full" in name else 0,
        0 if "smoke" in name else 1,
        name,
    )


def select_latest_file(run_dir, pattern):
    matches = sorted(Path(run_dir).glob(pattern))
    if not matches:
        return None
    return matches[-1]


def derive_run_dir_value(family_root, run_dirs):
    if len(run_dirs) == 1:
        return run_dirs[0]
    basenames = set(Path(path).name for path in run_dirs)
    if len(basenames) == 1:
        return str(Path(family_root) / "shard_*" / list(basenames)[0])
    return str(family_root)


def derive_file_value(family_root, run_dirs, file_paths, pattern):
    if len(file_paths) == 1:
        return file_paths[0]
    basenames = set(Path(path).name for path in run_dirs)
    if len(basenames) == 1:
        return str(Path(family_root) / "shard_*" / list(basenames)[0] / pattern)
    return file_paths[0]


if __name__ == "__main__":
    raise SystemExit(main())
