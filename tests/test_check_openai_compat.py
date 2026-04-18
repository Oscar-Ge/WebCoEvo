import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_openai_compat.py"


def _start_server(routes):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route = self.server.routes[("GET", self.path)]
            self.server.requests.append(("GET", self.path, None, dict(self.headers)))
            if callable(route):
                status, headers, body = route("GET", self.path, None, dict(self.headers))
            else:
                status, headers, body = route
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            route = self.server.routes[("POST", self.path)]
            self.server.requests.append(("POST", self.path, body, dict(self.headers)))
            if callable(route):
                status, headers, response_body = route("POST", self.path, body, dict(self.headers))
            else:
                status, headers, response_body = route
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response_body)

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.routes = routes
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _run_check(base_url, output_file):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--base-url",
            base_url,
            "--api-key",
            "test-key",
            "--model",
            "gpt-5.4",
            "--output-file",
            str(output_file),
        ],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )


def test_check_openai_compat_normalizes_v1_endpoints_and_reports_success(tmp_path):
    routes = {
        (
            "GET",
            "/v1/models",
        ): (
            200,
            {"Content-Type": "application/json"},
            json.dumps({"data": [{"id": "gpt-5.4"}, {"id": "other-model"}]}).encode("utf-8"),
        ),
        (
            "POST",
            "/v1/chat/completions",
        ): (
            200,
            {"Content-Type": "application/json"},
            json.dumps({"choices": [{"message": {"content": "OK"}}]}).encode("utf-8"),
        ),
    }
    server, thread = _start_server(routes)
    try:
        output_file = tmp_path / "api_smoke.json"
        base_url = "http://127.0.0.1:{}/v1".format(server.server_port)
        result = _run_check(base_url, output_file)

        assert result.returncode == 0, result.stderr
        payload = json.loads(output_file.read_text(encoding="utf-8"))
        assert payload["ok"] is True
        assert payload["provider_models_ok"] is True
        assert payload["model_available"] is True
        assert payload["chat_ok"] is True
        assert payload["response_excerpt"] == "OK"
        assert [request[:2] for request in server.requests] == [
            ("GET", "/v1/models"),
            ("POST", "/v1/chat/completions"),
        ]
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_check_openai_compat_writes_failure_report_for_missing_model_and_non_json_chat(tmp_path):
    routes = {
        (
            "GET",
            "/v1/models",
        ): (
            200,
            {"Content-Type": "application/json"},
            json.dumps({"data": [{"id": "different-model"}]}).encode("utf-8"),
        ),
        (
            "POST",
            "/v1/chat/completions",
        ): (
            200,
            {"Content-Type": "text/plain"},
            b"not-json",
        ),
    }
    server, thread = _start_server(routes)
    try:
        output_file = tmp_path / "api_smoke.json"
        base_url = "http://127.0.0.1:{}/v1/".format(server.server_port)
        result = _run_check(base_url, output_file)

        assert result.returncode == 2
        payload = json.loads(output_file.read_text(encoding="utf-8"))
        assert payload["ok"] is False
        assert payload["provider_models_ok"] is True
        assert payload["model_available"] is False
        assert payload["chat_ok"] is False
        assert "chat_error" in payload
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_check_openai_compat_accepts_models_403_and_uses_streaming_responses_fallback(tmp_path):
    def _responses_route(method, path, body, headers):
        del method, path
        payload = json.loads(body)
        if payload.get("stream"):
            lines = [
                "event: response.output_text.delta",
                'data: {"type":"response.output_text.delta","delta":"O"}',
                "",
                "event: response.output_text.delta",
                'data: {"type":"response.output_text.delta","delta":"K"}',
                "",
                "event: response.completed",
                'data: {"type":"response.completed","response":{"status":"completed"}}',
                "",
            ]
            return (
                200,
                {"Content-Type": "text/event-stream"},
                "\n".join(lines).encode("utf-8"),
            )
        return (
            200,
            {"Content-Type": "application/json"},
            json.dumps({"status": "completed", "output": []}).encode("utf-8"),
        )

    routes = {
        (
            "GET",
            "/v1/models",
        ): (
            403,
            {"Content-Type": "text/plain"},
            b"error code: 1010",
        ),
        (
            "POST",
            "/v1/chat/completions",
        ): (
            200,
            {"Content-Type": "application/json"},
            json.dumps({"choices": [{"message": {"role": "assistant"}}]}).encode("utf-8"),
        ),
        (
            "POST",
            "/v1/responses",
        ): _responses_route,
    }
    server, thread = _start_server(routes)
    try:
        output_file = tmp_path / "api_smoke.json"
        base_url = "http://127.0.0.1:{}/v1".format(server.server_port)
        result = _run_check(base_url, output_file)

        assert result.returncode == 0, result.stderr
        payload = json.loads(output_file.read_text(encoding="utf-8"))
        assert payload["ok"] is True
        assert payload["provider_models_ok"] is False
        assert payload["chat_ok"] is True
        assert payload["generation_endpoint"] == "responses_stream"
        assert payload["response_excerpt"] == "OK"
        assert [request[:2] for request in server.requests] == [
            ("GET", "/v1/models"),
            ("POST", "/v1/chat/completions"),
            ("POST", "/v1/responses"),
            ("POST", "/v1/responses"),
        ]
        for request in server.requests[1:]:
            headers = request[3]
            assert headers.get("User-Agent", "").startswith("curl/")
    finally:
        server.shutdown()
        thread.join(timeout=5)
