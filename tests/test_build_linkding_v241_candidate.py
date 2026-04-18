import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_linkding_v241_candidate.py"


def _start_server():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body)
            self.server.requests.append(
                {
                    "path": self.path,
                    "headers": dict(self.headers),
                    "payload": payload,
                }
            )

            if self.path == "/v1/chat/completions":
                response = {"choices": [{"message": {"role": "assistant"}}]}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode("utf-8"))
                return

            if self.path == "/v1/responses":
                if payload.get("stream"):
                    proposal_payload = {
                        "summary": {
                            "preserve_patterns": [
                                "Preserve task-specific login next redirects after authentication."
                            ],
                            "lost_patterns": [
                                "Filtered bookmark destinations were replaced by release_lookup fallback routes."
                            ],
                            "required_gap_phrases": ["login next", "filtered bookmark"],
                        },
                        "proposals": [
                            {
                                "operation": "edit_rule",
                                "target_rule_id": "xvr24_0004",
                                "reason": "Keep the original filtered destination after login.",
                                "rule": {
                                    "title": "Preserve login next redirects and filtered bookmark destinations",
                                    "scope": {"drift_types": ["content", "functional"]},
                                    "trigger": {
                                        "old_assumption": "A generic prepared route is a safe replacement after login.",
                                        "observed_symptoms": [
                                            "The task starts from login?next=.../bookmarks?q=...",
                                            "After login, the agent routes to release_lookup=prepared instead of the requested filtered bookmark view.",
                                        ],
                                    },
                                    "adaptation_strategy": [
                                        "Keep the task-specific next destination and preserve the requested filtered bookmark query after login.",
                                        "If the filtered bookmark URL is already loaded, finalize immediately instead of overwriting it with a generic fallback route.",
                                    ],
                                    "verification_check": [
                                        "The post-login URL still targets the requested /bookmarks?q=... destination."
                                    ],
                                    "forbidden_actions": [
                                        "Do not replace a requested filtered bookmark destination with release_lookup=prepared."
                                    ],
                                },
                                "support": {
                                    "gap_ids": ["login_next_lost"],
                                    "supporting_task_ids": [1600303, 1600307],
                                },
                            },
                            {"operation": "keep_rule", "target_rule_id": "xvr24_0007"},
                        ],
                    }
                    wrapped = "Draft summary\n```json\n{}\n```\nThanks".format(
                        json.dumps(proposal_payload, ensure_ascii=False)
                    )
                    stream_lines = []
                    for chunk in [wrapped[:60], wrapped[60:140], wrapped[140:]]:
                        if not chunk:
                            continue
                        stream_lines.extend(
                            [
                                "event: response.output_text.delta",
                                "data: {}".format(
                                    json.dumps(
                                        {
                                            "type": "response.output_text.delta",
                                            "delta": chunk,
                                        },
                                        ensure_ascii=False,
                                    )
                                ),
                                "",
                            ]
                        )
                    stream_lines.extend(
                        [
                            "event: response.completed",
                            'data: {"type":"response.completed","response":{"status":"completed"}}',
                            "",
                        ]
                    )
                    body_text = "\n".join(stream_lines)
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.end_headers()
                    self.wfile.write(body_text.encode("utf-8"))
                    return

                response = {"status": "completed", "output": []}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode("utf-8"))
                return

            self.send_response(404)
            self.end_headers()

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_build_linkding_v241_candidate_cli_writes_rulebook_raw_outputs_and_fallback_summary(tmp_path):
    server, thread = _start_server()
    try:
        artifacts_dir = tmp_path / "artifacts" / "reflection" / "v2_4_1"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        rulebooks_dir = tmp_path / "rulebooks"
        rulebooks_dir.mkdir(parents=True, exist_ok=True)
        base_rulebook = rulebooks_dir / "v2_4.json"
        output_rulebook = rulebooks_dir / "v2_4_1.json"
        manifest_file = artifacts_dir / "run_manifest.json"
        api_smoke_file = artifacts_dir / "api_smoke.json"
        casebook_file = artifacts_dir / "focus20_casebook.md"
        mining_cases_file = artifacts_dir / "focus20_mining_cases.jsonl"
        transition_file = artifacts_dir / "focus20_transition_first_modified_to_hardv3.json"

        base_rulebook.write_text(
            json.dumps(
                {
                    "artifact_type": "cross_version_reflection_rules",
                    "version": "v2_4",
                    "rules": [
                        {
                            "rule_id": "xvr24_0004",
                            "title": "Preserve task-specific login next parameters and never replace them with generic examples",
                            "scope": {"drift_types": ["content", "functional"]},
                            "trigger": {
                                "old_assumption": "A generic next destination is fine.",
                                "observed_symptoms": ["The task starts from login?next=..."],
                            },
                            "adaptation_strategy": ["Preserve the task-specific next target."],
                            "verification_check": ["The redirected page still matches the requested target."],
                            "forbidden_actions": ["Do not replace next with a generic route."],
                        },
                        {
                            "rule_id": "xvr24_0007",
                            "title": "For filtered bookmark tasks, treat query-state arrival as completion evidence",
                            "scope": {"drift_types": ["content", "functional"]},
                            "trigger": {
                                "old_assumption": "Arrival on the filtered bookmark view is not enough to finish.",
                                "observed_symptoms": ["The filtered bookmark URL already matches the task."],
                            },
                            "adaptation_strategy": ["Finalize once the filtered bookmark URL already matches."],
                            "verification_check": ["The URL still contains the requested query."],
                            "forbidden_actions": ["Do not leave the filtered bookmark view after success."],
                        },
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        manifest_file.write_text(json.dumps({"focus20": {"first_modified": {}, "hardv3": {}}}, indent=2), encoding="utf-8")
        api_smoke_file.write_text(
            json.dumps({"ok": True, "chat_ok": True, "generation_endpoint": "responses_stream"}, indent=2),
            encoding="utf-8",
        )
        casebook_file.write_text(
            "\n".join(
                [
                    "# focus20 Casebook",
                    "",
                    "## Transition Counts",
                    "- `both_success`: 1",
                    "- `lost`: 1",
                    "",
                    "## Representative `lost` Excerpts",
                    "- task 1600303 (`content` / `lost`)",
                    "  right: repeated goto('/login/?next=%2Fbookmarks%3Frelease_lookup%3Dprepared') after login",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        mining_cases_file.write_text("", encoding="utf-8")
        transition_file.write_text(
            json.dumps(
                {
                    "summary": {"transition_counts": {"both_success": 1, "lost": 1}, "num_rows": 2},
                    "comparison": {"left_label": "first_modified_v2_4", "right_label": "hardv3_v2_4"},
                    "rows": [
                        {
                            "task_id": 1600303,
                            "source_task_id": 16003,
                            "focus20_source_task_id": 16003,
                            "family": "F16003",
                            "variant": "content",
                            "drift_type": "content",
                            "intent": "Authenticate and land on a filtered bookmarks view.",
                            "transition": "lost",
                            "start_url": "http://localhost:9104/login?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter",
                            "left_success": True,
                            "right_success": False,
                            "left_error": "",
                            "right_error": "max_steps_no_success",
                            "left_trace_excerpt": [
                                {
                                    "step": 0,
                                    "action": "click('login')",
                                    "model_output": "",
                                    "url": "http://localhost:9104/bookmarks?q=focus20-login-filter",
                                    "error": "",
                                    "final_answer": "",
                                }
                            ],
                            "right_trace_excerpt": [
                                {
                                    "step": 0,
                                    "action": "goto('http://localhost:9104/login/?next=%2Fbookmarks%3Frelease_lookup%3Dprepared')",
                                    "model_output": "",
                                    "url": "http://localhost:9104/bookmarks?release_lookup=prepared",
                                    "error": "",
                                    "final_answer": "",
                                }
                            ],
                        },
                        {
                            "task_id": 1600304,
                            "source_task_id": 16003,
                            "focus20_source_task_id": 16003,
                            "family": "F16003",
                            "variant": "content",
                            "drift_type": "content",
                            "intent": "Authenticate and land on a filtered bookmarks view.",
                            "transition": "both_success",
                            "start_url": "http://localhost:9104/login?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter",
                            "left_success": True,
                            "right_success": True,
                            "left_error": "",
                            "right_error": "",
                            "left_trace_excerpt": [],
                            "right_trace_excerpt": [],
                        },
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--base-url",
                "http://127.0.0.1:{}/v1".format(server.server_port),
                "--api-key",
                "test-key",
                "--model",
                "gpt-5.4",
                "--base-rulebook",
                str(base_rulebook),
                "--manifest-file",
                str(manifest_file),
                "--casebook-file",
                str(casebook_file),
                "--mining-cases",
                str(mining_cases_file),
                "--output-rulebook",
                str(output_rulebook),
                "--output-dir",
                str(artifacts_dir),
            ],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        assert result.returncode == 0, result.stderr
        candidate = json.loads(output_rulebook.read_text(encoding="utf-8"))
        assert candidate["version"] == "v2_4_1"
        assert candidate["rule_count"] == 2
        assert candidate["rules"][0]["title"] == "Preserve login next redirects and filtered bookmark destinations"

        raw_payload = json.loads((artifacts_dir / "gpt54_proposals_raw.json").read_text(encoding="utf-8"))
        assert raw_payload["selected_transport"] == "responses_stream"
        assert "```json" in raw_payload["response_text"]

        summary = json.loads((artifacts_dir / "gpt54_candidate_summary.json").read_text(encoding="utf-8"))
        assert summary["proposal_summary"]["accepted"] == 2
        assert summary["proposal_summary"]["rejected"] == 0
        assert summary["evidence"]["mode"] == "transition_casebook_fallback"
        assert "login next" in summary["required_gap_phrases"]
        assert "filtered bookmark" in summary["required_gap_phrases"]
        assert summary["provider_summary"]["lost_patterns"] == [
            "Filtered bookmark destinations were replaced by release_lookup fallback routes."
        ]

        assert [request["path"] for request in server.requests] == [
            "/v1/chat/completions",
            "/v1/responses",
            "/v1/responses",
        ]
        for request in server.requests:
            assert request["headers"].get("User-Agent", "").startswith("curl/")
    finally:
        server.shutdown()
        thread.join(timeout=5)
