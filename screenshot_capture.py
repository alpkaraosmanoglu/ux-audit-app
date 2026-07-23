"""Auto-capture a screenshot of a competitor URL via ScreenshotOne's API.

This is an optional convenience for the competitor benchmarking flow: instead
of a designer manually screenshotting a competitor's page, they can paste the
URL and pull a live capture in one click. BYOK, same as the Anthropic key —
the ScreenshotOne access key lives only in st.session_state for the session.

API docs: https://screenshotone.com/docs/getting-started/
"""

import requests

SCREENSHOTONE_ENDPOINT = "https://api.screenshotone.com/take"

DEFAULT_TIMEOUT = 25  # seconds — full-page captures of heavy sites can be slow


class ScreenshotCaptureError(Exception):
    """Raised when a capture fails, with a message safe to show in the UI."""


def capture_url_screenshot(
    access_key: str,
    url: str,
    full_page: bool = True,
    viewport_width: int = 1440,
    viewport_height: int = 900,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Capture a screenshot of `url` and return it in the same shape used
    throughout the app for screenshot dicts: {"name", "data", "mime_type"}.

    Raises ScreenshotCaptureError with a user-safe message on any failure
    (bad key, invalid/unreachable URL, quota exceeded, timeout).
    """
    if not access_key:
        raise ScreenshotCaptureError("No screenshot API key configured.")
    if not url or not url.strip():
        raise ScreenshotCaptureError("No URL provided.")

    params = {
        "access_key": access_key,
        "url": url.strip(),
        "format": "png",
        "full_page": "true" if full_page else "false",
        "viewport_width": viewport_width,
        "viewport_height": viewport_height,
        "block_cookie_banners": "true",
        "block_ads": "true",
        "cache": "false",
    }

    try:
        resp = requests.get(SCREENSHOTONE_ENDPOINT, params=params, timeout=timeout)
    except requests.exceptions.Timeout:
        raise ScreenshotCaptureError("Capture timed out — the page may be slow or unreachable.")
    except requests.exceptions.RequestException as e:
        raise ScreenshotCaptureError(f"Network error while capturing screenshot: {e}")

    content_type = resp.headers.get("Content-Type", "")

    if resp.status_code != 200:
        # ScreenshotOne returns structured JSON errors on failure.
        message = f"Screenshot capture failed (HTTP {resp.status_code})."
        try:
            err = resp.json()
            detail = err.get("error_message") or err.get("message")
            if detail:
                message = f"Screenshot capture failed: {detail}"
        except ValueError:
            pass
        raise ScreenshotCaptureError(message)

    if not content_type.startswith("image/"):
        raise ScreenshotCaptureError("Screenshot capture did not return an image — check the URL and try again.")

    name = url.strip().replace("https://", "").replace("http://", "").rstrip("/")
    return {"name": name, "data": resp.content, "mime_type": content_type}
