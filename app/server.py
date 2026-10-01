"""Serve the lightweight V3 executive insight interface."""

from __future__ import annotations

import json
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from finance_ai.config import AIConfig
from finance_ai.evidence import build_evidence_package
from finance_ai.presentation import presentation_payload
from finance_ai.providers.openai_provider import OpenAIInsightProvider
from finance_ai.service import ExecutiveInsightService, InsightGenerationError


STATIC_ROOT = PROJECT_ROOT / "app" / "static"
DATABASE_PATH = PROJECT_ROOT / "data" / "curated" / "finance_analytics.duckdb"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


class ExecutiveAppHandler(BaseHTTPRequestHandler):
    server_version = "FinanceInsightsV3/1.0"

    def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        content = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _send_static(self, file_name: str, content_type: str) -> None:
        content = (STATIC_ROOT / file_name).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in STATIC_FILES:
            self._send_static(*STATIC_FILES[path])
            return
        if path == "/api/context":
            try:
                context = build_evidence_package(DATABASE_PATH)
                payload = presentation_payload(context)
                payload["aiConfigured"] = bool(os.getenv("OPENAI_API_KEY"))
                self._send_json(payload)
            except Exception as exc:
                self._send_json(
                    {"error": {"category": "context_build_failed", "message": "Verified finance context is unavailable.", "detail": type(exc).__name__}},
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/insights":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not os.getenv("OPENAI_API_KEY"):
            self._send_json(
                {"error": {"category": "provider_not_configured", "message": "AI generation is unavailable until the server-side API key is configured."}},
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return
        try:
            context = build_evidence_package(DATABASE_PATH)
            config = AIConfig.from_environment()
            if config.provider != "openai":
                raise ValueError("Unsupported AI provider")
            output = ExecutiveInsightService(OpenAIInsightProvider(config)).generate(context)
            self._send_json(presentation_payload(context, output))
        except InsightGenerationError as exc:
            self._send_json({"error": exc.diagnostic.model_dump(mode="json")}, HTTPStatus.UNPROCESSABLE_ENTITY)
        except Exception as exc:
            self._send_json(
                {"error": {"category": "generation_failed", "message": "Executive AI insights could not be generated safely.", "detail": type(exc).__name__}},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"{self.address_string()} - {format_string % args}")


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), ExecutiveAppHandler)
    print(f"Finance Insights V3 running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run(port=int(os.getenv("PORT", "8000")))
