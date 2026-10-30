"""poli_page_render: smoke-test the Django integration end-to-end.

Renders a PDF using the lazy client, writes it to disk, and surfaces
PoliPageError families via mapped exit codes. The API key's environment selects
the published copy of the project that gets rendered.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from poli_page import (
    APIConnectionError,
    APIStatusError,
    InternalServerError,
    PoliPageError,
    RenderInput,
)

from django_poli_page._client import client


class Command(BaseCommand):
    help = "Smoke-test the Poli Page integration by rendering a template end-to-end."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--project", help="Project slug (required)")
        parser.add_argument("--template", help="Template slug (required)")
        parser.add_argument("--data", default="{}", help="Inline JSON for the data payload")
        parser.add_argument("--data-file", help="Read data payload from a file ('-' for stdin)")
        parser.add_argument(
            "--output",
            "-o",
            default="./poli-page-render.pdf",
            help="Output file path (default: ./poli-page-render.pdf)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        data = self._resolve_data(options)
        try:
            self._do_pdf(options, data)
        except PoliPageError as exc:
            self.stderr.write(self.style.ERROR(self._format_error(exc)))
            sys.exit(self._exit_code_for(exc))

    def _do_pdf(self, options: dict[str, Any], data: dict[str, Any]) -> None:
        project = options.get("project")
        template = options.get("template")
        if not project or not template:
            raise CommandError("--project and --template are required.")

        input_payload: RenderInput = {
            "project": project,
            "template": template,
            "data": data,
        }

        start = time.perf_counter()
        pdf = client.render.pdf(input_payload)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(pdf)

        self.stdout.write(
            self.style.SUCCESS(
                f"Rendered {len(pdf)} bytes in {elapsed_ms}ms. Wrote to {output}.",
            ),
        )

    def _resolve_data(self, options: dict[str, Any]) -> dict[str, Any]:
        data_file = options.get("data_file")
        if data_file is not None:
            contents = sys.stdin.read() if data_file == "-" else self._read_file(data_file)
        else:
            contents = options["data"]
        if not contents:
            return {}
        try:
            decoded = json.loads(contents)
        except json.JSONDecodeError as exc:
            raise CommandError(f"--data / --data-file must be valid JSON: {exc}") from exc
        if not isinstance(decoded, dict):
            raise CommandError("--data / --data-file must decode to a JSON object.")
        return decoded

    @staticmethod
    def _read_file(path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    @staticmethod
    def _format_error(exc: PoliPageError) -> str:
        return (
            f"{type(exc).__name__}: {exc.message} "
            f"(status={exc.status}, code={exc.code}, request_id={exc.request_id})"
        )

    @staticmethod
    def _exit_code_for(exc: PoliPageError) -> int:
        if isinstance(exc, APIConnectionError):
            return 3
        if isinstance(exc, InternalServerError):
            return 2
        if isinstance(exc, APIStatusError) and exc.status is not None:
            if 400 <= exc.status < 500:
                return 1
            if exc.status >= 500:
                return 2
        return 4
