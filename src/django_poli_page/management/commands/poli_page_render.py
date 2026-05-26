"""poli_page_render: smoke-test the Django integration end-to-end.

Renders a PDF (or HTML preview with --preview) using the lazy client, writes it
to disk, and surfaces PoliPageError families via mapped exit codes.

Option naming note (spec §9.2): Django's BaseCommand reserves --verbosity / -v
/ --settings / --pythonpath / --traceback / --no-color / --force-color /
--skip-checks. We deliberately use --template-version (not --version) for
forward-compat consistency with the symfony-bundle's same choice.
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
    InlineModeInput,
    InternalServerError,
    PoliPageError,
    ProjectModeInput,
)

from django_poli_page._client import client


class Command(BaseCommand):
    help = "Smoke-test the Poli Page integration by rendering a template end-to-end."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--project", help="Project slug (required unless --html given)")
        parser.add_argument("--template", help="Template slug (required)")
        parser.add_argument(
            "--template-version",
            dest="template_version",
            help="Template version (required unless --html given)",
        )
        parser.add_argument("--data", default="{}", help="Inline JSON for the data payload")
        parser.add_argument("--data-file", help="Read data payload from a file ('-' for stdin)")
        parser.add_argument(
            "--html", help="Inline-mode: render raw HTML from a file (preview only)"
        )
        parser.add_argument(
            "--output",
            "-o",
            default="./poli-page-render.pdf",
            help="Output file path (default: ./poli-page-render.pdf)",
        )
        parser.add_argument(
            "--preview",
            action="store_true",
            help="Render HTML preview instead of PDF; writes to .html",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        data = self._resolve_data(options)
        try:
            if options["preview"]:
                self._do_preview(options, data)
            else:
                self._do_pdf(options, data)
        except PoliPageError as exc:
            self.stderr.write(self.style.ERROR(self._format_error(exc)))
            sys.exit(self._exit_code_for(exc))

    def _do_pdf(self, options: dict[str, Any], data: dict[str, Any]) -> None:
        project = options.get("project")
        template = options.get("template")
        version = options.get("template_version")
        if not project or not template or not version:
            raise CommandError(
                "--project, --template and --template-version are required for PDF rendering.",
            )

        input_payload: ProjectModeInput = {
            "project": project,
            "template": template,
            "version": version,
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

    def _do_preview(self, options: dict[str, Any], data: dict[str, Any]) -> None:
        html_path = options.get("html")
        template = options.get("template")
        project = options.get("project")
        version = options.get("template_version")

        preview_input: ProjectModeInput | InlineModeInput
        if html_path:
            html_text = self._read_file(html_path)
            preview_input = InlineModeInput(template=html_text, data=data)
        else:
            if not project or not template or not version:
                raise CommandError(
                    "Either --html, or all of --project --template --template-version, "
                    "are required for preview.",
                )
            preview_input = {
                "project": project,
                "template": template,
                "version": version,
                "data": data,
            }

        start = time.perf_counter()
        result = client.render.preview(preview_input)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        out_path = Path(options["output"])
        if out_path.suffix == ".pdf":
            out_path = out_path.with_suffix(".html")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result.html, encoding="utf-8")

        self.stdout.write(
            self.style.SUCCESS(
                f"Rendered {result.total_pages} pages of HTML preview in {elapsed_ms}ms. "
                f"Wrote to {out_path}.",
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
