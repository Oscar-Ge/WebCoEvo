from urllib.parse import urlparse

try:
    import requests
except Exception:  # pragma: no cover - optional runtime dependency
    requests = None


def is_local_start_url(url):
    parsed = urlparse(str(url or ""))
    return (parsed.hostname or "").strip().lower() in set(["localhost", "127.0.0.1"])


def health_url_for_start_url(start_url):
    parsed = urlparse(str(start_url or ""))
    if not parsed.scheme or not parsed.netloc:
        return ""
    return "{}://{}/".format(parsed.scheme, parsed.netloc)


def check_runtime_health(start_url, timeout=5):
    if requests is None:
        return {"ok": False, "url": health_url_for_start_url(start_url), "error": "requests_unavailable"}
    url = health_url_for_start_url(start_url)
    if not url:
        return {"ok": False, "url": "", "error": "invalid_start_url"}
    try:
        response = requests.get(url, timeout=timeout)
        return {
            "ok": response.status_code < 500,
            "url": url,
            "status_code": response.status_code,
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}
