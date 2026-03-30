"""
HTTP handler shaped for AWS Lambda + API Gateway (HTTP API / REST proxy integration).

Also used by Vercel: `api/convert.py` imports `lambda_handler` (serverless).

Request JSON:
{
  "imageUrl": "https://.../image.jpg"
}
OR
{
  "imageBase64": "....",
  "imageMimeType": "image/png"
}

Response JSON:
{
  "imageBase64": "....",
  "imageMimeType": "image/png"
}
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict
from urllib.parse import urlparse

import requests
from PIL import Image
from PIL.Image import UnidentifiedImageError


def _cors_headers() -> Dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


def _json_response(status_code: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {**_cors_headers(), "Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body")
    if not body:
        return {}
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8")
    return json.loads(body)


def _base_browser_headers() -> Dict[str, str]:
    # Many hosts block bare requests or return HTML without a browser-like User-Agent.
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _referer_header_sets(url: str) -> list[Dict[str, str]]:
    """Different CDNs expect Referer/Origin; try several before giving up."""
    u = url.strip()
    p = urlparse(u)
    if not p.scheme or not p.netloc:
        return [{}]

    origin = f"{p.scheme}://{p.netloc}"
    variants: list[Dict[str, str]] = [
        {"Referer": origin, "Origin": origin},
        {"Referer": origin + "/"},
    ]
    # Parent path (e.g. gallery page) as referer
    if "/" in (p.path or "").rstrip("/"):
        parent = u.rsplit("/", 1)[0]
        if parent.startswith("http") and parent != u:
            variants.append({"Referer": parent + "/", "Origin": origin})
    variants.append({"Referer": u})

    seen: set[frozenset[tuple[str, str]]] = set()
    out: list[Dict[str, str]] = []
    for item in variants:
        key = frozenset(item.items())
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _resolve_imgbb_page_to_direct_url(url: str) -> str:
    """
    ImgBB gallery links (https://ibb.co/xxxx) return HTML. The real file is on i.ibb.co
    and is listed in og:image. See https://imgbb.com/ — use "Direct link" in the UI,
    or we resolve it here when the user pastes the page URL.
    """
    p = urlparse(url.strip())
    host = (p.netloc or "").lower().replace("www.", "")
    if host != "ibb.co":
        return url
    path = (p.path or "").strip("/")
    if not path or path.split("/")[0] in ("upload", "plugin", "api", "tos", "privacy"):
        return url

    # Fetch HTML page (not subject to image hotlink rules on the same response)
    html_headers = {
        **_base_browser_headers(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://ibb.co/",
    }
    try:
        page = requests.get(url, timeout=30, headers=html_headers, allow_redirects=True)
        page.raise_for_status()
    except requests.exceptions.RequestException:
        return url

    text = page.text
    for pattern in (
        r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
        r'<meta\s+property=["\']og:image:secure_url["\']\s+content=["\']([^"\']+)["\']',
        r'<link\s+rel=["\']image_src["\']\s+href=["\']([^"\']+)["\']',
    ):
        m = re.search(pattern, text, re.I)
        if m:
            direct = m.group(1).replace("&amp;", "&").strip()
            if direct.startswith("http") and "ibb" in direct.lower():
                return direct
    return url


def _extension_for_pil_format(fmt: str | None) -> str:
    if not fmt:
        return "png"
    f = fmt.upper()
    return {
        "JPEG": "jpg",
        "JPG": "jpg",
        "PNG": "png",
        "WEBP": "webp",
        "GIF": "gif",
        "BMP": "bmp",
        "MPO": "jpg",
        "TIFF": "tiff",
    }.get(f, "png")


def _save_image_from_url(url: str, input_path: str) -> str:
    url = _resolve_imgbb_page_to_direct_url(url.strip()) or url.strip()

    base = _base_browser_headers()
    last_problem = "no response"

    for extra in _referer_header_sets(url):
        headers = {**base, **extra}
        try:
            resp = requests.get(url, timeout=30, headers=headers, allow_redirects=True)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            last_problem = str(e)
            continue

        content = resp.content
        if not content:
            last_problem = "empty body"
            continue

        head = content.lstrip()[:200].lower()
        if head.startswith(b"<") or head.startswith(b"<!doctype"):
            last_problem = "HTML instead of image (hotlink or bot block)"
            continue

        try:
            with Image.open(io.BytesIO(content)) as img:
                ext = _extension_for_pil_format(img.format)
        except UnidentifiedImageError:
            last_problem = "bytes are not a known image format"
            continue

        out = f"{input_path}.{ext}"
        with open(out, "wb") as f:
            f.write(content)
        return out

    raise ValueError(
        "Could not fetch a usable image from this URL. "
        "Use a direct link to the image file (often ends in .jpg / .png / .webp), "
        "open the image alone in a new tab and copy that URL, or upload the file. "
        f"Last issue: {last_problem}"
    )


def _save_image_from_base64(image_base64: str, input_path: str, image_mime_type: str) -> str:
    ext = "png"
    ct = (image_mime_type or "image/png").split(";")[0].strip().lower()
    if ct in ("image/jpeg", "image/jpg"):
        ext = "jpg"
    elif ct == "image/webp":
        ext = "webp"
    elif ct == "image/gif":
        ext = "gif"
    elif ct == "image/png":
        ext = "png"

    input_file = f"{input_path}.{ext}"
    with open(input_file, "wb") as f:
        f.write(base64.b64decode(image_base64))
    return input_file


def _run_converter(input_path: str, output_path: str) -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    converter_script = os.path.join(here, "image_to_ascii.py")

    # Converter CLI contract:
    #   python image_to_ascii.py --input <input_path> --output <output_path>
    subprocess.run(
        [sys.executable, converter_script, "--input", input_path, "--output", output_path],
        check=True,
        capture_output=True,
        text=True,
    )


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    if event.get("httpMethod") == "OPTIONS" or event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return {"statusCode": 200, "headers": _cors_headers(), "body": ""}

    try:
        payload = _parse_body(event)

        image_url = payload.get("imageUrl")
        image_base64 = payload.get("imageBase64")
        image_mime_type = str(payload.get("imageMimeType") or "image/png")

        if not image_url and not image_base64:
            return _json_response(400, {"error": "Provide `imageUrl` or `imageBase64`."})

        with tempfile.TemporaryDirectory() as tmpdir:
            input_base = os.path.join(tmpdir, "input")
            if image_base64:
                input_path = _save_image_from_base64(str(image_base64), input_base, image_mime_type)
            else:
                input_path = _save_image_from_url(str(image_url), input_base)

            output_path = os.path.join(tmpdir, "output.png")
            _run_converter(input_path, output_path)

            with open(output_path, "rb") as f:
                out_bytes = f.read()

        out_b64 = base64.b64encode(out_bytes).decode("utf-8")
        return _json_response(200, {"imageBase64": out_b64, "imageMimeType": "image/png"})

    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        stdout = (e.stdout or "").strip()
        return _json_response(
            500,
            {
                "error": "Converter failed.",
                "details": stderr or stdout or str(e),
            },
        )
    except requests.exceptions.RequestException as e:
        return _json_response(400, {"error": "Failed to fetch image URL.", "details": str(e)})
    except ValueError as e:
        return _json_response(400, {"error": str(e)})
    except Exception as e:
        msg = e if isinstance(e, str) else (e.args[0] if getattr(e, "args", None) else str(e))
        return _json_response(500, {"error": "Server error.", "details": str(msg)})
