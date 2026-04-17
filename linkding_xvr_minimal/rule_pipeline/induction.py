import re


SPECIFIC_RULE_GUIDANCE = "\n".join(
    [
        "Specificity requirements:",
        "- Task-specific rules are allowed and preferred over generic advice.",
        "- Use concrete details when justified: exact credentials, URLs, redirect parameters, target pages, and visible completion cues.",
        "- Avoid vague rules like 'be careful' or 'verify carefully'.",
        "- Return 1 to 3 ExpeL rule operations when there is enough evidence.",
    ]
)


def _slugify(text):
    value = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return value or "insight"


def _tokenize_terms(*texts):
    tokens = []
    seen = set()
    for text in texts:
        for token in re.findall(r"[a-z0-9]+", str(text or "").lower()):
            if len(token) <= 1 or token in seen:
                continue
            seen.add(token)
            tokens.append(token)
    return tokens


def build_reflection_prompt(episode):
    lines = [
        "You are extracting ExpeL-style transferable insights from a web-agent episode.",
        "Task ID: {}".format(episode.get("task_id")),
        "Family: {}".format(episode.get("family", "")),
        "Source version: {}".format(episode.get("source_version", "")),
        "Goal: {}".format(episode.get("goal", "")),
        "Outcome: {}".format("success" if episode.get("success") else "failure"),
        "Error: {}".format(episode.get("error", "")),
    ]
    retry_guidance_text = str(episode.get("retry_guidance_text", "")).strip()
    if retry_guidance_text:
        lines.append("Retry guidance before this attempt: {}".format(retry_guidance_text))
    lines.append("Trajectory:")
    for step in episode.get("steps", []):
        lines.append(
            "- step {} | action={} | model_output={} | url={} | error={}".format(
                step.get("step", 0),
                step.get("action", ""),
                step.get("model_output", ""),
                step.get("url", ""),
                step.get("error", ""),
            )
        )
    lines.extend(
        [
            "",
            "Return a JSON array of concise insights. Each insight must include:",
            "- summary",
            "- when",
            "- query_terms",
        ]
    )
    return "\n".join(lines)


def _trajectory_lines(episode):
    lines = []
    retry_guidance_text = str(episode.get("retry_guidance_text", "")).strip()
    if retry_guidance_text:
        lines.append("- retry_guidance={}".format(retry_guidance_text))
    for step in episode.get("steps", []):
        lines.append(
            "- step {} | action={} | model_output={} | url={} | error={}".format(
                step.get("step", 0),
                step.get("action", ""),
                step.get("model_output", ""),
                step.get("url", ""),
                step.get("error", ""),
            )
        )
    return lines


def build_compare_critique_prompt(success_episode, fail_episode, existing_rules=None):
    rules = list(existing_rules or [])
    lines = [
        "You are updating an ExpeL rulebook for a web agent.",
        "Compare the successful and failed trajectories below and output only ExpeL rule operations.",
        "Allowed formats:",
        "ADD: <general rule ending with a period.>",
        "AGREE <n>: <existing rule text.>",
        "EDIT <n>: <revised rule text ending with a period.>",
        "REMOVE <n>: <existing rule text.>",
        "",
        "Successful task:",
        str(success_episode.get("goal", "")),
        "Successful trajectory:",
    ]
    lines.extend(_trajectory_lines(success_episode))
    lines.extend(
        [
            "",
            "Failed task:",
            str(fail_episode.get("goal", "")),
            "Failure error: {}".format(fail_episode.get("error", "")),
            "Failed trajectory:",
        ]
    )
    lines.extend(_trajectory_lines(fail_episode))
    if rules:
        lines.extend(["", "Existing rules:"])
        lines.extend(
            "{}. {}".format(index, rule)
            for index, rule in enumerate(rules, start=1)
        )
    return "\n".join(lines)


def build_success_critique_prompt(success_episodes, existing_rules=None):
    rules = list(existing_rules or [])
    lines = [
        "You are updating an ExpeL rulebook for a web agent.",
        "Generalize from the successful trajectories below and output only ExpeL rule operations.",
        "Allowed formats:",
        "ADD: <general rule ending with a period.>",
        "AGREE <n>: <existing rule text.>",
        "EDIT <n>: <revised rule text ending with a period.>",
        "REMOVE <n>: <existing rule text.>",
    ]
    if rules:
        lines.extend(["", "Existing rules:"])
        lines.extend(
            "{}. {}".format(index, rule)
            for index, rule in enumerate(rules, start=1)
        )
    lines.extend(["", "Successful trajectories:"])
    for index, episode in enumerate(success_episodes, start=1):
        lines.append("Success {}: {}".format(index, episode.get("goal", "")))
        lines.extend(_trajectory_lines(episode))
        lines.append("")
    return "\n".join(lines).strip()


def build_failure_critique_prompt(failure_episodes, existing_rules=None):
    rules = list(existing_rules or [])
    lines = [
        "You are updating an ExpeL rulebook for a web agent.",
        "Generalize from the failed trajectories below and output only ExpeL rule operations.",
        "Focus on reusable avoidance or recovery rules that would help future episodes avoid the same mistake.",
        "Allowed formats:",
        "ADD: <general rule ending with a period.>",
        "AGREE <n>: <existing rule text.>",
        "EDIT <n>: <revised rule text ending with a period.>",
        "REMOVE <n>: <existing rule text.>",
    ]
    if rules:
        lines.extend(["", "Existing rules:"])
        lines.extend(
            "{}. {}".format(index, rule)
            for index, rule in enumerate(rules, start=1)
        )
    lines.extend(["", "Failed trajectories:"])
    for index, episode in enumerate(failure_episodes, start=1):
        lines.append("Failure {}: {}".format(index, episode.get("goal", "")))
        lines.append("Failure error: {}".format(episode.get("error", "")))
        lines.extend(_trajectory_lines(episode))
        lines.append("")
    return "\n".join(lines).strip()


def build_specific_compare_prompt(success_episode, fail_episode, existing_rules=None):
    return build_compare_critique_prompt(
        success_episode,
        fail_episode,
        existing_rules=existing_rules,
    ) + "\n\n" + SPECIFIC_RULE_GUIDANCE


def build_task_recap_prompt(case, existing_rules=None):
    success_episode = dict(case.get("success_episode") or {})
    failure_episodes = list(case.get("failure_episodes", []) or [])
    existing_rules = list(existing_rules or [])
    lines = [
        "You are updating an ExpeL rulebook for a web agent.",
        "Use the single task case below to add highly specific rescue rules.",
        "Allowed formats:",
        "ADD: <rule ending with a period.>",
        "AGREE <n>: <existing rule text.>",
        "EDIT <n>: <revised rule text ending with a period.>",
        "REMOVE <n>: <existing rule text.>",
        "",
        "Task ID: {}".format(case.get("task_id")),
        "Goal: {}".format(case.get("goal", "")),
    ]
    if existing_rules:
        lines.extend(["", "Existing rules:"])
        lines.extend(
            "{}. {}".format(index, rule)
            for index, rule in enumerate(existing_rules, start=1)
        )
    if failure_episodes:
        lines.extend(["", "Failed trajectories:"])
        for index, episode in enumerate(failure_episodes, start=1):
            lines.append("Failure {}:".format(index))
            lines.append(build_reflection_prompt(episode))
            lines.append("")
    if success_episode:
        lines.extend(["Successful recovery trajectory:", build_reflection_prompt(success_episode)])
    lines.extend(["", SPECIFIC_RULE_GUIDANCE])
    return "\n".join(lines).strip()


def build_specific_success_prompt(success_episodes, existing_rules=None):
    return build_success_critique_prompt(
        success_episodes,
        existing_rules=existing_rules,
    ) + "\n\n" + SPECIFIC_RULE_GUIDANCE


def _normalize_query_terms(raw, episode):
    query_terms = raw.get("query_terms") or []
    if query_terms:
        return _tokenize_terms(*[str(value) for value in query_terms])
    return _tokenize_terms(
        raw.get("summary", ""),
        raw.get("when", ""),
        episode.get("family", ""),
        episode.get("goal", ""),
    )


def extract_insights_from_episode(episode, reflect_fn):
    prompt = build_reflection_prompt(episode)
    raw_rows = reflect_fn(prompt) or []
    insights = []
    for index, raw in enumerate(raw_rows):
        summary = str(raw.get("summary", "")).strip()
        if not summary:
            continue
        insights.append(
            {
                "insight_id": "expel.{}.{}.{}".format(
                    episode.get("task_id", "unknown"),
                    index,
                    _slugify(summary)[:64],
                ),
                "task_id": int(episode.get("task_id", 0)),
                "family": str(episode.get("family", "")),
                "source_version": str(episode.get("source_version", "")),
                "summary": summary,
                "when": str(raw.get("when", "")).strip(),
                "query_terms": _normalize_query_terms(raw, episode),
                "outcome_tag": "success" if episode.get("success") else "failure",
            }
        )
    return insights


def parse_rule_operations(llm_text):
    operations = []
    for raw_line in str(llm_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^(ADD|AGREE \d+|EDIT \d+|REMOVE \d+):\s+(.*)$", line)
        if not match:
            continue
        operation, text = match.groups()
        candidate = str(text or "").strip()
        if not candidate.endswith("."):
            continue
        operations.append((operation.strip(), candidate))
    return operations


def _normalize_rule_text(rule_text):
    return " ".join(str(rule_text or "").split()).strip()


def _retrieve_rule_index(rules, rule_text, rule_num=None):
    if rule_num is not None:
        rule_index = int(rule_num) - 1
        if 0 <= rule_index < len(rules):
            return rule_index
        return None
    normalized = _normalize_rule_text(rule_text)
    for index, row in enumerate(rules):
        text, _count = row
        if _normalize_rule_text(text) == normalized:
            return index
    return None


def _is_existing_rule(rules, rule_text):
    return _retrieve_rule_index(rules, rule_text) is not None


def update_rule_items(rules, operations, list_full=False):
    next_rules = list(rules)
    filtered_ops = list(operations)
    delete_indices = set()
    for index, row in enumerate(filtered_ops):
        operation, rule_text = row
        op_type = operation.split(" ")[0]
        rule_num = int(operation.split(" ")[1]) if " " in operation else None
        if op_type == "ADD":
            if _is_existing_rule(next_rules, rule_text):
                delete_indices.add(index)
        elif op_type == "EDIT":
            if _is_existing_rule(next_rules, rule_text):
                existing_index = _retrieve_rule_index(next_rules, rule_text)
                filtered_ops[index] = (
                    "AGREE {}".format(existing_index + 1),
                    next_rules[existing_index][0],
                )
            elif rule_num is None or rule_num > len(next_rules):
                delete_indices.add(index)
        elif op_type in set(["REMOVE", "AGREE"]):
            if _retrieve_rule_index(next_rules, rule_text, rule_num=rule_num) is None:
                delete_indices.add(index)
        else:
            delete_indices.add(index)

    filtered_ops = [
        filtered_ops[index]
        for index in range(len(filtered_ops))
        if index not in delete_indices
    ]
    for op_name in ("REMOVE", "AGREE", "EDIT", "ADD"):
        for operation, rule_text in filtered_ops:
            op_type = operation.split(" ")[0]
            if op_type != op_name:
                continue
            if op_type == "REMOVE":
                rule_num = int(operation.split(" ")[1]) if " " in operation else None
                rule_index = _retrieve_rule_index(next_rules, rule_text, rule_num=rule_num)
                if rule_index is None:
                    continue
                remove_strength = 3 if list_full else 1
                next_rules[rule_index] = (
                    next_rules[rule_index][0],
                    next_rules[rule_index][1] - remove_strength,
                )
            elif op_type == "AGREE":
                rule_num = int(operation.split(" ")[1]) if " " in operation else None
                rule_index = _retrieve_rule_index(next_rules, rule_text, rule_num=rule_num)
                if rule_index is None:
                    continue
                next_rules[rule_index] = (
                    next_rules[rule_index][0],
                    next_rules[rule_index][1] + 1,
                )
            elif op_type == "EDIT":
                rule_index = int(operation.split(" ")[1]) - 1
                if 0 <= rule_index < len(next_rules):
                    next_rules[rule_index] = (
                        rule_text,
                        next_rules[rule_index][1] + 1,
                    )
            elif op_type == "ADD":
                next_rules.append((rule_text, 2))
    next_rules = [row for row in next_rules if row[1] > 0]
    next_rules.sort(key=lambda row: (-row[1], row[0]))
    return next_rules


def _chunked(rows, size):
    size = max(1, int(size))
    return [list(rows[index : index + size]) for index in range(0, len(rows), size)]


def extract_insight_rows(episodes, reflect_fn):
    insights = []
    seen = set()
    for episode in episodes:
        for insight in extract_insights_from_episode(episode, reflect_fn=reflect_fn):
            key = (
                int(insight.get("task_id", 0)),
                str(insight.get("summary", "")).strip().lower(),
                str(insight.get("outcome_tag", "")),
            )
            if key in seen:
                continue
            seen.add(key)
            insights.append(insight)
    return insights


def mine_specific_rules_from_cases(
    cases,
    critique_fn,
    max_num_rules=20,
    success_critique_num=1,
):
    rule_items = []
    rule_metadata = {}
    generation_records = []

    def _record_rule_metadata(rule_text, episodes, evidence_mode, task_id):
        row = rule_metadata.setdefault(
            rule_text,
            {
                "version_tags": set(),
                "provenance_episode_ids": set(),
                "source_task_ids": set(),
                "evidence_modes": set(),
            },
        )
        row["evidence_modes"].add(str(evidence_mode))
        row["source_task_ids"].add(int(task_id))
        for episode in episodes:
            version = str(episode.get("source_version", "") or episode.get("version", "")).strip()
            if version:
                row["version_tags"].add(version)
            episode_id = str(episode.get("episode_id", "")).strip()
            if episode_id:
                row["provenance_episode_ids"].add(episode_id)

    def _apply_ops(prompt_type, task_id, prompt, response, supporting_episodes):
        operations = parse_rule_operations(response)
        generation_records.append(
            {
                "prompt_type": prompt_type,
                "task_id": int(task_id),
                "prompt": prompt,
                "response": response,
                "operations": [
                    {"operation": operation, "text": text}
                    for operation, text in operations
                ],
            }
        )
        for _operation, rule_text in operations:
            _record_rule_metadata(
                rule_text,
                supporting_episodes,
                evidence_mode=prompt_type,
                task_id=task_id,
            )
        return update_rule_items(
            rule_items,
            operations,
            list_full=max_num_rules + 5 <= len(rule_items),
        )

    for case in cases:
        success_episode = dict(case.get("success_episode") or {})
        failures = list(case.get("failure_episodes", []) or [])
        for fail_episode in failures:
            if len(rule_items) >= int(max_num_rules):
                break
            prompt = build_specific_compare_prompt(
                success_episode,
                fail_episode,
                existing_rules=[text for text, _score in rule_items],
            )
            response = str(critique_fn(prompt) or "").strip()
            rule_items = _apply_ops(
                "mixed",
                int(case.get("task_id", 0)),
                prompt,
                response,
                [success_episode, fail_episode],
            )
        if len(rule_items) >= int(max_num_rules):
            break

    if len(rule_items) < int(max_num_rules):
        for case in cases:
            if len(rule_items) >= int(max_num_rules):
                break
            prompt = build_task_recap_prompt(
                case,
                existing_rules=[text for text, _score in rule_items],
            )
            response = str(critique_fn(prompt) or "").strip()
            supporting_episodes = list(case.get("failure_episodes", []) or [])
            success_episode = case.get("success_episode") or {}
            if success_episode:
                supporting_episodes.append(success_episode)
            rule_items = _apply_ops(
                "task_recap",
                int(case.get("task_id", 0)),
                prompt,
                response,
                supporting_episodes,
            )

    if len(rule_items) < int(max_num_rules):
        success_rows = [
            dict(case.get("success_episode") or {})
            for case in cases
            if case.get("success_episode")
        ]
        for chunk in _chunked(success_rows, success_critique_num):
            if len(rule_items) >= int(max_num_rules):
                break
            prompt = build_specific_success_prompt(
                chunk,
                existing_rules=[text for text, _score in rule_items],
            )
            response = str(critique_fn(prompt) or "").strip()
            representative_task_id = int(chunk[0].get("task_id", 0)) if chunk else 0
            rule_items = _apply_ops(
                "success_only",
                representative_task_id,
                prompt,
                response,
                chunk,
            )

    rules = []
    for index, row in enumerate(rule_items[: max(0, int(max_num_rules))], start=1):
        text, score = row
        meta = rule_metadata.get(text, {})
        rules.append(
            {
                "rule_id": "rule.{}".format(index),
                "text": text,
                "score": int(score),
                "scope": "global",
                "scope_id": "",
                "version_tags": sorted(meta.get("version_tags", set())),
                "source_task_ids": sorted(meta.get("source_task_ids", set())),
                "provenance_episode_ids": sorted(meta.get("provenance_episode_ids", set())),
                "support_count": len(meta.get("provenance_episode_ids", set())),
                "evidence_mode": "+".join(sorted(meta.get("evidence_modes", set()))) or "unknown",
            }
        )
    return rules, generation_records
