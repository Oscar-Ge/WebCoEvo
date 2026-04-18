"""Parse and validate structured reflection-rule proposals."""

import json
import os
import re
import urllib.error
import urllib.request


ALLOWED_OPERATIONS = set(["add_rule", "edit_rule", "keep_rule", "drop_rule"])
RULE_REQUIRED_FIELDS = [
    "title",
    "scope",
    "trigger",
    "adaptation_strategy",
    "verification_check",
    "forbidden_actions",
]
TASK_SCOPE_KEYS = set(
    [
        "task_id",
        "task_ids",
        "source_task_id",
        "source_task_ids",
        "focus20_source_task_id",
        "focus20_source_task_ids",
    ]
)
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_USER_AGENT = "curl/8.7.1"
DEFAULT_TIMEOUT_SEC = 120


def extract_json_payload(text):
    if isinstance(text, (dict, list)):
        return text
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("empty proposal text")

    for fenced in re.findall(r"```(?:json)?\s*(.*?)```", raw, flags=re.IGNORECASE | re.DOTALL):
        try:
            return json.loads(fenced.strip())
        except ValueError:
            continue

    try:
        return json.loads(raw)
    except ValueError:
        pass

    decoder = json.JSONDecoder()
    starts = [index for index, char in enumerate(raw) if char in set(["{", "["])]
    for start in starts:
        try:
            payload, _ = decoder.raw_decode(raw[start:])
            return payload
        except ValueError:
            continue
    raise ValueError("no JSON object or array found in proposal text")


def normalize_proposal(raw):
    row = dict(raw or {})
    operation = str(row.get("operation") or row.get("op") or row.get("action") or "").strip()
    target_rule_id = str(
        row.get("target_rule_id")
        or row.get("target_id")
        or row.get("existing_rule_id")
        or row.get("rule_id")
        or ""
    ).strip()
    rule = row.get("rule")
    if rule is None:
        rule = row.get("proposed_rule")
    if isinstance(rule, dict):
        rule = dict(rule)
    else:
        rule = {}
    return {
        "operation": operation,
        "target_rule_id": target_rule_id,
        "rule": rule,
        "reason": str(row.get("reason") or row.get("rationale") or "").strip(),
        "support": _as_dict(row.get("support")),
        "raw": row,
    }


def validate_proposal(proposal, allow_task_scope=False):
    row = normalize_proposal(proposal)
    errors = []
    operation = row["operation"]
    if operation not in ALLOWED_OPERATIONS:
        errors.append("unknown_operation")
        return errors
    if operation in set(["edit_rule", "keep_rule", "drop_rule"]) and not row["target_rule_id"]:
        errors.append("missing_target_rule_id")
    if operation in set(["add_rule", "edit_rule"]):
        rule = dict(row.get("rule") or {})
        missing = [field for field in RULE_REQUIRED_FIELDS if _is_empty(rule.get(field))]
        if missing:
            errors.append("missing_rule_fields")
        if not allow_task_scope and _contains_task_scope(rule):
            errors.append("task_scope_not_allowed")
    return errors


def parse_rule_proposals(text, allow_task_scope=False):
    payload = extract_json_payload(text)
    raw_proposals = _proposal_rows(payload)
    accepted = []
    rejected = []
    for index, raw in enumerate(raw_proposals):
        proposal = normalize_proposal(raw)
        errors = validate_proposal(proposal, allow_task_scope=allow_task_scope)
        if errors:
            rejected.append({"index": index, "errors": errors, "proposal": proposal})
        else:
            accepted.append(proposal)
    return {
        "schema_version": "webcoevo-xvr-rule-proposals-v1",
        "accepted": accepted,
        "rejected": rejected,
        "raw_payload": payload,
    }


def build_reflection_proposal_prompt(cases, base_rules):
    prompt = {
        "task": "Propose compact cross-version reflection rulebook edits.",
        "constraints": [
            "Return only JSON with schema_version and proposals.",
            "Allowed operations: add_rule, edit_rule, keep_rule, drop_rule.",
            "For add_rule/edit_rule include title, scope, trigger, adaptation_strategy, verification_check, forbidden_actions.",
            "Use drift_types scope by default. Do not use task_ids unless explicitly allowed by the caller.",
            "Keep rules mechanism-level and grounded in the supplied mining cases.",
        ],
        "proposal_schema": {
            "schema_version": "webcoevo-xvr-rule-proposals-v1",
            "proposals": [
                {
                    "operation": "edit_rule",
                    "target_rule_id": "existing_rule_id",
                    "rule": {},
                    "support": {"gap_ids": [], "supporting_task_ids": []},
                }
            ],
        },
        "base_rules": list(base_rules or []),
        "mining_cases": list(cases or []),
    }
    return json.dumps(prompt, indent=2, sort_keys=True)


def build_stub_proposal_fn(path):
    def proposal_fn(prompt):
        del prompt
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()

    return proposal_fn


def request_openai_compatible_text(
    prompt,
    base_url=None,
    api_key=None,
    model=None,
    system_prompt="You output only valid JSON reflection-rule proposals.",
):
    resolved_base_url = str(base_url or os.environ.get("OPENAI_BASE_URL") or DEFAULT_OPENAI_BASE_URL).rstrip(
        "/"
    )
    resolved_api_key = str(api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
    resolved_model = str(model or os.environ.get("OPENAI_MODEL") or "gpt-5.4").strip()
    attempts = []

    chat_body = {
        "model": resolved_model,
        "messages": [
            {"role": "system", "content": str(system_prompt or "").strip()},
            {"role": "user", "content": str(prompt or "")},
        ],
        "temperature": 0,
    }
    chat_url = build_chat_completions_url(resolved_base_url)
    chat_attempt = _try_generation_attempt(
        url=chat_url,
        method="POST",
        api_key=resolved_api_key,
        body=chat_body,
        accept="application/json",
        transport="chat_completions",
        text_extractor=_extract_chat_text_from_body,
    )
    attempts.append(chat_attempt)
    if chat_attempt.get("text"):
        return _selected_generation_report(
            resolved_base_url,
            resolved_model,
            chat_attempt,
            attempts,
        )

    responses_body = {
        "model": resolved_model,
        "instructions": str(system_prompt or "").strip(),
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": str(prompt or ""),
                    }
                ],
            }
        ],
        "store": False,
        "stream": False,
        "include": ["reasoning.encrypted_content"],
    }
    responses_url = build_responses_url(resolved_base_url)
    responses_attempt = _try_generation_attempt(
        url=responses_url,
        method="POST",
        api_key=resolved_api_key,
        body=responses_body,
        accept="application/json",
        transport="responses_json",
        text_extractor=_extract_responses_text_from_body,
    )
    attempts.append(responses_attempt)
    if responses_attempt.get("text"):
        return _selected_generation_report(
            resolved_base_url,
            resolved_model,
            responses_attempt,
            attempts,
        )

    stream_body = dict(responses_body)
    stream_body["stream"] = True
    stream_attempt = _try_generation_attempt(
        url=responses_url,
        method="POST",
        api_key=resolved_api_key,
        body=stream_body,
        accept="text/event-stream",
        transport="responses_stream",
        text_extractor=_extract_streamed_responses_text_from_body,
    )
    attempts.append(stream_attempt)
    if stream_attempt.get("text"):
        return _selected_generation_report(
            resolved_base_url,
            resolved_model,
            stream_attempt,
            attempts,
        )

    raise RuntimeError(
        "No usable generation text from provider: {}".format(
            json.dumps(
                [
                    {
                        "transport": attempt.get("transport"),
                        "url": attempt.get("url"),
                        "status": attempt.get("status"),
                        "error": attempt.get("error"),
                        "empty_text": attempt.get("empty_text", False),
                    }
                    for attempt in attempts
                ],
                sort_keys=True,
            )
        )
    )


def build_openai_proposal_fn(base_url=None, api_key=None, model=None):
    def proposal_fn(prompt):
        return request_openai_compatible_text(
            prompt=prompt,
            base_url=base_url,
            api_key=api_key,
            model=model,
            system_prompt="You output only valid JSON reflection-rule proposals.",
        )["text"]

    return proposal_fn


def build_chat_completions_url(base_url):
    normalized = str(base_url or "").rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return normalized + "/chat/completions"


def build_responses_url(base_url):
    normalized = str(base_url or "").rstrip("/")
    if normalized.endswith("/responses"):
        return normalized
    return normalized + "/responses"


def build_request_headers(api_key, accept="application/json"):
    headers = {
        "Authorization": "Bearer {}".format(str(api_key or "").strip()),
        "Accept": str(accept or "application/json"),
        "User-Agent": DEFAULT_USER_AGENT,
    }
    if accept == "text/event-stream":
        headers["Cache-Control"] = "no-cache"
    return headers


def _try_generation_attempt(url, method, api_key, body, accept, transport, text_extractor):
    attempt = {
        "transport": transport,
        "url": url,
        "status": None,
        "content_type": "",
        "response_body": "",
        "text": "",
        "error": "",
        "empty_text": False,
    }
    try:
        response = _request_text(
            url=url,
            method=method,
            api_key=api_key,
            body=body,
            accept=accept,
        )
        attempt["status"] = response.get("status")
        attempt["content_type"] = response.get("content_type", "")
        attempt["response_body"] = response.get("body", "")
        attempt["text"] = str(text_extractor(attempt["response_body"]) or "").strip()
        attempt["empty_text"] = not bool(attempt["text"])
    except Exception as exc:
        attempt["error"] = str(exc)
    return attempt


def _selected_generation_report(base_url, model, selected_attempt, attempts):
    return {
        "text": selected_attempt["text"],
        "selected_transport": selected_attempt["transport"],
        "selected_endpoint": selected_attempt["url"],
        "selected_response_body": selected_attempt["response_body"],
        "base_url": base_url,
        "model": model,
        "attempts": attempts,
    }


def _request_text(url, method, api_key, body=None, accept="application/json", timeout=DEFAULT_TIMEOUT_SEC):
    headers = build_request_headers(api_key=api_key, accept=accept)
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=int(timeout or DEFAULT_TIMEOUT_SEC)) as response:
            raw_body = response.read().decode("utf-8", errors="replace")
            return {
                "status": response.getcode(),
                "content_type": response.headers.get("Content-Type", ""),
                "body": raw_body,
            }
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            "HTTP {} for {} {}: {}".format(
                exc.code,
                method,
                url,
                error_body[:400],
            )
        )


def _extract_chat_text_from_body(body):
    payload = json.loads(body)
    if not isinstance(payload, dict):
        return ""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    return _coerce_text_content(message.get("content"))


def _extract_responses_text_from_body(body):
    payload = json.loads(body)
    return _extract_responses_text(payload)


def _extract_streamed_responses_text_from_body(body):
    deltas = []
    completed_text = ""
    for raw_line in str(body or "").splitlines():
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            payload = json.loads(data)
        except ValueError:
            continue
        payload_type = str(payload.get("type") or "").strip()
        if payload_type == "response.output_text.delta":
            delta = str(payload.get("delta") or "")
            if delta:
                deltas.append(delta)
        elif payload_type == "response.completed":
            completed_text = _extract_responses_text(payload.get("response"))
    text = "".join(deltas).strip()
    if text:
        return text
    return completed_text.strip()


def _extract_responses_text(payload):
    if not isinstance(payload, dict):
        return ""
    top_level = _coerce_text_content(payload.get("output_text"))
    if top_level:
        return top_level
    parts = []
    for item in list(payload.get("output") or []):
        if not isinstance(item, dict):
            continue
        text = _coerce_text_content(item.get("content"))
        if text:
            parts.append(text)
    return "".join(parts).strip()


def _coerce_text_content(content):
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                if item.get("type") in set(["text", "output_text", "input_text"]) and text:
                    parts.append(text)
                elif text:
                    parts.append(text)
        return "".join(parts).strip()
    if isinstance(content, dict):
        text = str(content.get("text") or "").strip()
        if text:
            return text
    return ""


def _proposal_rows(payload):
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        rows = payload.get("proposals") or payload.get("items") or payload.get("rules") or []
        if isinstance(rows, dict):
            return [rows]
        return [row for row in list(rows or []) if isinstance(row, dict)]
    return []


def _contains_task_scope(rule):
    if not isinstance(rule, dict):
        return False
    for key in TASK_SCOPE_KEYS:
        if not _is_empty(rule.get(key)):
            return True
    scope = rule.get("scope")
    if isinstance(scope, dict):
        return any(not _is_empty(scope.get(key)) for key in TASK_SCOPE_KEYS)
    return False


def _as_dict(value):
    if isinstance(value, dict):
        return dict(value)
    return {}


def _is_empty(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False
