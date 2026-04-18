#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linkding_xvr_minimal.rule_pipeline.reflection_proposals import (
    DEFAULT_USER_AGENT,
    request_openai_compatible_text,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--env-file", default="")
    parser.add_argument("--output-file", required=True)
    return parser.parse_args(argv)


def normalize_base_url(base_url):
    value = str(base_url or "").strip().rstrip("/")
    if not value:
        raise ValueError("base_url is required")
    return value


def build_models_url(base_url):
    normalized = normalize_base_url(base_url)
    if normalized.endswith("/models"):
        return normalized
    return normalized + "/models"


def build_chat_completions_url(base_url):
    normalized = normalize_base_url(base_url)
    if normalized.endswith("/chat/completions"):
        return normalized
    return normalized + "/chat/completions"


def extract_model_ids(payload):
    if isinstance(payload, dict):
        rows = payload.get("data")
        if isinstance(rows, list):
            return [str(row.get("id") or "").strip() for row in rows if isinstance(row, dict)]
    return []


def parse_chat_response(payload):
    if not isinstance(payload, dict):
        raise ValueError("chat payload must be a JSON object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("chat payload missing choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("chat payload choice must be an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ValueError("chat payload missing message")
    content = message.get("content")
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
        content = "".join(parts)
    content = str(content or "").strip()
    if not content:
        raise ValueError("chat payload missing message content")
    return {"content": content}


def main(argv=None):
    args = parse_args(argv)
    config = resolve_provider_config(
        base_url=args.base_url,
        api_key=args.api_key,
        model=args.model,
        env_file=args.env_file,
    )
    report = run_check(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
    )
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


def run_check(base_url, api_key, model):
    normalized_base_url = normalize_base_url(base_url)
    report = {
        "ok": False,
        "provider_models_ok": False,
        "model_available": False,
        "chat_ok": False,
        "model": str(model or "").strip(),
        "base_url": normalized_base_url,
        "models_url": build_models_url(normalized_base_url),
        "chat_completions_url": build_chat_completions_url(normalized_base_url),
        "generation_endpoint": "",
        "user_agent": DEFAULT_USER_AGENT,
    }

    try:
        models_payload = _request_json(
            url=report["models_url"],
            method="GET",
            api_key=api_key,
        )
        model_ids = extract_model_ids(models_payload)
        report["provider_models_ok"] = True
        report["provider_models_count"] = len(model_ids)
        report["model_available"] = report["model"] in model_ids
        report["provider_model_ids"] = model_ids
    except Exception as exc:
        report["models_error"] = str(exc)

    try:
        generation = request_openai_compatible_text(
            prompt="Reply with OK only.",
            base_url=normalized_base_url,
            api_key=api_key,
            model=report["model"],
            system_prompt="You are a helpful assistant. Reply with OK only.",
        )
        report["chat_ok"] = True
        report["generation_endpoint"] = str(generation.get("selected_transport") or "")
        report["response_excerpt"] = str(generation.get("text") or "")[:200]
    except Exception as exc:
        report["chat_error"] = str(exc)

    report["ok"] = bool(report["chat_ok"])
    return report


def _request_json(url, method, api_key, body=None):
    headers = {
        "Authorization": "Bearer {}".format(str(api_key or "").strip()),
        "Accept": "application/json",
        "User-Agent": DEFAULT_USER_AGENT,
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content_type = response.headers.get("Content-Type", "")
            raw_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            "HTTP {} for {} {}: {}".format(exc.code, method, url, error_body[:400])
        )

    try:
        return json.loads(raw_body)
    except ValueError:
        parsed_url = urllib.parse.urlparse(url)
        endpoint = parsed_url.path or url
        if content_type:
            raise ValueError(
                "Non-JSON response from {} (content-type {}): {}".format(
                    endpoint,
                    content_type,
                    raw_body[:200],
                )
            )
        raise ValueError("Non-JSON response from {}: {}".format(endpoint, raw_body[:200]))


def load_env_file(path):
    env = {}
    if not path:
        return env
    env_path = Path(path)
    if not env_path.exists():
        raise FileNotFoundError("env file not found: {}".format(env_path))
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def resolve_provider_config(base_url="", api_key="", model="", env_file=""):
    file_env = load_env_file(env_file)
    resolved_base_url = str(
        base_url
        or file_env.get("OPENAI_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or ""
    ).strip()
    resolved_api_key = str(
        api_key
        or file_env.get("OPENAI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    ).strip()
    resolved_model = str(
        model
        or file_env.get("UITARS_MODEL")
        or os.environ.get("UITARS_MODEL")
        or os.environ.get("OPENAI_MODEL")
        or "gpt-5.4"
    ).strip()
    if not resolved_base_url:
        raise ValueError("base_url is required")
    if not resolved_api_key:
        raise ValueError("api_key is required")
    return {
        "base_url": resolved_base_url,
        "api_key": resolved_api_key,
        "model": resolved_model,
    }


if __name__ == "__main__":
    raise SystemExit(main())
