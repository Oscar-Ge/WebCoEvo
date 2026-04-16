from linkding_xvr_minimal.runtime import health_url_for_start_url, is_local_start_url


def test_health_url_for_start_url_uses_origin():
    assert (
        health_url_for_start_url("http://localhost:9103/login?next=/bookmarks")
        == "http://localhost:9103/"
    )


def test_is_local_start_url_detects_localhost_and_loopback():
    assert is_local_start_url("http://localhost:9103")
    assert is_local_start_url("http://127.0.0.1:9103")
    assert not is_local_start_url("https://example.com")
