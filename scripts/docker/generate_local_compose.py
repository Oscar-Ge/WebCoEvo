#!/usr/bin/env python3
import argparse
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "scripts" / "singularity" / "linkding_drift_manifest.py"
DEFAULT_IMAGE = "sissbruecker/linkding:1.45.0"


def load_manifest():
    spec = importlib.util.spec_from_file_location("linkding_drift_manifest", MANIFEST_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LINKDING_DRIFT_VARIANTS


def quote(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def bind_mount_block(source, target, read_only=True):
    lines = [
        "      - type: bind",
        "        source: {}".format(quote(source)),
        "        target: {}".format(quote(target)),
    ]
    if read_only:
        lines.append("        read_only: true")
    return "\n".join(lines)


def generate_compose(variant, host_port, image, runner_dockerfile):
    variants = load_manifest()
    if variant not in variants:
        known = ", ".join(sorted(variants))
        raise SystemExit("Unknown variant '{}'. Known variants: {}".format(variant, known))

    data_dir = ROOT / ".docker" / "linkding-data" / variant
    tmp_dir = ROOT / ".docker" / "linkding-tmp" / variant
    data_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    bind_blocks = [
        bind_mount_block(data_dir, "/etc/linkding/data", read_only=False),
        bind_mount_block(tmp_dir, "/etc/linkding/tmp", read_only=False),
    ]
    for bind in variants[variant].get("bind_mounts", []):
        bind_blocks.append(bind_mount_block(bind["source"], bind["target"], read_only=True))

    volumes = "\n".join(bind_blocks)
    dockerfile = str(Path(runner_dockerfile).as_posix())
    return """services:
  linkding:
    image: {image}
    ports:
      - {port_mapping}
    volumes:
{volumes}
    environment:
      LD_SUPERUSER_NAME: baseline
      LD_SUPERUSER_PASSWORD: Baseline123!
      LD_DISABLE_BACKGROUND_TASKS: "True"

  runner:
    build:
      context: {root}
      dockerfile: {dockerfile}
    working_dir: /workspace
    volumes:
      - type: bind
        source: {root}
        target: /workspace
    environment:
      PYTHONPATH: /workspace
      OPENAI_API_KEY: ${{OPENAI_API_KEY:-}}
      OPENAI_BASE_URL: ${{OPENAI_BASE_URL:-http://host.docker.internal:8000/v1}}
      UITARS_MODEL: ${{UITARS_MODEL:-Qwen/Qwen3-VL-30B-A3B-Instruct}}
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - linkding
""".format(
        image=quote(image),
        port_mapping=quote("{}:9090".format(host_port)),
        volumes=volumes,
        root=quote(str(ROOT)),
        dockerfile=quote(dockerfile),
    )


def main():
    parser = argparse.ArgumentParser(description="Generate a local Docker Compose file for one Linkding drift variant.")
    parser.add_argument("--variant", default="access")
    parser.add_argument("--host-port", type=int, default=9103)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--runner-dockerfile", default="docker/Dockerfile.runner")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        generate_compose(
            variant=args.variant,
            host_port=args.host_port,
            image=args.image,
            runner_dockerfile=args.runner_dockerfile,
        ),
        encoding="utf-8",
    )
    print(out)


if __name__ == "__main__":
    main()
