"""
Vercel serverless entry: this file becomes POST /api/convert.

Local dev (from repo root):
  python -m uvicorn api.convert:app --host 127.0.0.1 --port 8000

Routes on the dev server: POST / and POST /convert (same handler). CORS is enabled so
http://localhost:5174 can call http://127.0.0.1:8000 directly if you set VITE_API_URL.

Prefer same-origin /api/convert + Vite proxy (no CORS): leave VITE_API_URL unset.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from lib.handler import lambda_handler

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _convert(request: Request) -> Response:
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8") if body_bytes else ""

    event: Dict[str, Any] = {
        "httpMethod": "POST",
        "body": body_str or json.dumps({}),
        "isBase64Encoded": False,
    }

    res = lambda_handler(event, None)
    return Response(
        status_code=int(res.get("statusCode", 200)),
        headers=res.get("headers", {}),
        media_type="application/json",
        content=res.get("body", ""),
    )


@app.post("/")
async def post_convert_root(request: Request) -> Response:
    return await _convert(request)


@app.post("/convert")
async def post_convert_path(request: Request) -> Response:
    return await _convert(request)

# @app.post("/")
# async def post_convert_path(request: Request) -> Response:
#     return await _convert(request)
