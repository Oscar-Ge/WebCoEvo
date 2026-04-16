from linkding_xvr_minimal.vl_message_utils import build_user_message_with_image


def test_build_user_message_with_image_uses_openai_content_parts():
    message = build_user_message_with_image("hello", b"abc")

    assert message["role"] == "user"
    assert message["content"][0]["type"] == "text"
    assert message["content"][0]["text"] == "hello"
    assert message["content"][1]["type"] == "image_url"
    assert message["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_build_user_message_with_image_encodes_numpy_array_as_png():
    numpy = __import__("numpy")
    image = numpy.zeros((2, 2, 3), dtype=numpy.uint8)

    message = build_user_message_with_image("hello", image)

    url = message["content"][1]["image_url"]["url"]
    assert url.startswith("data:image/png;base64,iVBOR")
