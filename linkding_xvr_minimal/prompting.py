from urllib.parse import parse_qs, urlparse

from linkding_xvr_minimal.vl_message_utils import build_user_message_with_image


def action_output_contract():
    return "\n".join(
        [
            "Output contract:",
            "- Respond with exactly one BrowserGym action inside triple backticks.",
            "- Do not add explanations, observations, plans, labels, or any prose before or after the fenced action.",
            "- Do not output headings like Observe/Plan/Verify.",
            "- Never output placeholder labels like `login` or `tagged`; output only a valid BrowserGym action such as `click('43')` or `send_msg_to_user(\"done\")`.",
        ]
    )


def build_text_only_action_prompt(obs, goal, action_set, observation_char_limit):
    html = _observation_html(obs, observation_char_limit)
    return {
        "role": "user",
        "content": """
You are helping a user to accomplish the following goal on a website:

{goal}

To do so, you can interact with the environment using the following actions:

{actions}

The inputs to those functions are the bids given in the html.

Here is the current state of the website, in the form of an html:

{html}

The action you provide must be in between triple ticks and leverage the 'bid=' information provided in the html.
Here is an example of how to use the bid action:

```
click('a314')
```

{contract}

Please provide a single action at a time and wait for the next observation. Provide only a single action per step.
Focus on the bid that are given in the html, and use them to perform the actions.
""".strip().format(
                goal=str(goal or ""),
                actions=action_set.describe(with_long_description=False),
                html=html,
                contract=action_output_contract(),
            ),
    }


def build_vl_action_prompt(obs, goal, action_set, observation_char_limit):
    if obs.get("screenshot") is None:
        raise ValueError("vl_action_reflection requires obs['screenshot']")
    text = """
You are helping a user to accomplish the following goal on a website:

{goal}

To do so, you can interact with the environment using the following actions:

{actions}

Use both the screenshot and the structured page state below.

{observation}

Action grounding contract:
- The screenshot is for visual disambiguation only.
- All executable bids or ids must come from the AX Tree or HTML Snapshot.
- If a bid is not present in the AX Tree or HTML Snapshot, do not use it.

The action you provide must be in between triple ticks and use the grounded bids from the AX Tree or HTML Snapshot.
Here is an example of how to use the bid action:

```
click('a314')
```

{contract}

Please provide a single action at a time and wait for the next observation. Provide only a single action per step.
""".strip().format(
        goal=str(goal or ""),
        actions=action_set.describe(with_long_description=False),
        observation=_vl_observation_text(obs, observation_char_limit),
        contract=action_output_contract(),
    )
    return build_user_message_with_image(text, obs.get("screenshot"))


def append_cross_version_rules_prompt(messages, selection_result):
    block = selection_result.get("rendered_block") or ""
    if block:
        messages.append({"role": "user", "content": block})
    return messages


def build_hardv3_task_guidance(obs, task_metadata):
    url = str((obs or {}).get("url") or task_metadata.get("start_url") or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.path.startswith("/bookmarks/new"):
        return ""

    axtree = str((obs or {}).get("axtree_txt") or "")
    html = str((obs or {}).get("pruned_html") or (obs or {}).get("dom_txt") or "")
    evidence = "\n".join([axtree, html])
    lower = evidence.lower()
    visible_lower = axtree.lower()
    params = parse_qs(parsed.query, keep_blank_values=True)
    expected_url = _first_query_value(params, "url")
    expected_title = _first_query_value(params, "title")
    expected_tags = _first_query_value(params, "tag_names")
    required_words = _required_completion_words(
        str(task_metadata.get("goal") or (obs or {}).get("goal") or "")
    )

    lines = []
    if (
        "review editable fields" in visible_lower
        or "release capture review" in visible_lower
        or "release workflow checkpoint" in visible_lower
    ):
        lines.extend(
            [
                "## Hardv3 bookmark checkpoint",
                "A visible staged continuation is present on the bookmark flow.",
                "- Click one visible continuation such as `Review editable fields` instead of `noop()`.",
                "- After the continuation reveals the editable form, reassess the URL, Title, and Tags fields before any further action.",
                "- Do not return to `/login` and do not repeat the same continuation click twice.",
                "- Do not noop on the staged checkpoint page.",
            ]
        )
        return "\n".join(lines)

    if "textbox 'tags'" not in lower and "id_tag_string" not in lower and "tags" not in lower:
        return ""

    title_visible = bool(expected_title and expected_title.lower() in lower)
    url_visible = bool(expected_url and expected_url.lower() in lower)
    tags_visible = bool(expected_tags and expected_tags.lower() in lower)
    tags_empty = _tags_field_looks_empty(axtree, html)

    lines = [
        "## Hardv3 bookmark completion check",
        "You are on the editable bookmark form. Verify the visible URL, Title, and Tags fields against the prefilled query values before acting.",
    ]
    if expected_tags and tags_empty:
        lines.extend(
            [
                "- The `Tags` field is visible but still empty.",
                "- Fill the visible Tags field with `{}` before stopping.".format(expected_tags),
                "- Do not `noop()` while the visible Tags field is still empty.",
            ]
        )
    if url_visible and title_visible and (tags_visible or not expected_tags):
        lines.append(
            "- The requested prefilled values are already visible. Finish with `send_msg_to_user(...)` instead of more browser actions."
        )
    elif not expected_tags:
        lines.append("- If the requested URL and Title are already visible, finish with `send_msg_to_user(...)`.")
    else:
        lines.append("- Only stop once the visible Tags field also reflects `{}`.".format(expected_tags))
        lines.append("- As soon as the visible URL, Title, and Tags fields all match, finish with `send_msg_to_user(...)`.")

    if required_words:
        lines.append(
            "- When you finish, include these completion words in `send_msg_to_user(...)`: {}.".format(
                ", ".join("`{}`".format(word) for word in required_words)
            )
        )
    return "\n".join(lines)


def _observation_html(obs, char_limit):
    for key in ("pruned_html", "axtree_txt", "dom_txt"):
        candidate = obs.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate[: int(char_limit)]
    return ""


def _vl_observation_text(obs, char_limit):
    sections = ["Current URL:\n" + str(obs.get("url") or "").strip()]
    axtree = str(obs.get("axtree_txt") or "").strip()
    html = str(obs.get("pruned_html") or obs.get("dom_txt") or "").strip()
    if axtree:
        sections.append("AX Tree:\n" + axtree[: int(char_limit)])
    if html:
        sections.append("HTML Snapshot:\n" + html[: int(char_limit)])
    last_error = str(obs.get("last_action_error") or "").strip()
    if last_error:
        sections.append("Last action error:\n" + last_error)
    return "\n\n".join(section for section in sections if section.strip())


def _first_query_value(params, key):
    values = params.get(key) or []
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _required_completion_words(goal):
    text = str(goal or "")
    lower = text.lower()
    marker = "include "
    idx = lower.find(marker)
    if idx < 0:
        return []
    tail = text[idx + len(marker) :]
    words = []
    quote = ""
    current = []
    for char in tail:
        if quote:
            if char == quote:
                word = "".join(current).strip()
                if word:
                    words.append(word)
                current = []
                quote = ""
            else:
                current.append(char)
            continue
        if char in {"'", '"'}:
            quote = char
        elif words and char == ".":
            break
    return words


def _tags_field_looks_empty(axtree, html):
    axtree_text = str(axtree or "")
    html_text = str(html or "")
    tag_lines = [line.strip() for line in axtree_text.splitlines() if "textbox 'Tags'" in line]
    if tag_lines:
        for line in tag_lines:
            if "value=" in line:
                return "value=''" in line or 'value=""' in line
        return True
    if "id_tag_string" in html_text:
        lowered = html_text.lower()
        if "id_tag_string" in lowered and 'value=""' in lowered:
            return True
        if "id_tag_string" in lowered and "value=''" in lowered:
            return True
    return False
