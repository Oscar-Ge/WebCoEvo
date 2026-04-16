import base64
import io


def build_user_message_with_image(text, image):
    raw = _image_to_png_bytes(image)
    encoded = base64.b64encode(raw).decode("ascii")
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": str(text or "")},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + encoded}},
        ],
    }


def _image_to_png_bytes(image):
    if isinstance(image, bytes):
        return image
    if hasattr(image, "save"):
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
    try:
        from PIL import Image

        if hasattr(image, "__array__"):
            pil_image = Image.fromarray(image.__array__())
            buffer = io.BytesIO()
            pil_image.save(buffer, format="PNG")
            return buffer.getvalue()
    except Exception:
        pass
    return bytes(image)
