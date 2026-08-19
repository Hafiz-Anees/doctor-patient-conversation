"""
core/middleware.py — runs on every response the app sends, before it goes
out. Currently used to strip out any field whose value is empty (None, "",
[], {}) so the frontend only ever sees fields that actually have data.
"""
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from utils.json_helpers import remove_empty_fields


class HideEmptyFieldsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return response

        # Read the full response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        try:
            data = json.loads(body)
            cleaned = remove_empty_fields(data)
            new_body = json.dumps(cleaned).encode("utf-8")
        except Exception:
            # If anything goes wrong parsing/cleaning, send the original,
            # unmodified response rather than breaking the request.
            new_body = body

        new_headers = dict(response.headers)
        new_headers["content-length"] = str(len(new_body))

        return Response(
            content=new_body,
            status_code=response.status_code,
            headers=new_headers,
            media_type="application/json",
        )