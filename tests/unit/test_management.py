from __future__ import annotations

import io
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from django.core.management import call_command


def _stub_client(
    mocker: Any,
    *,
    pdf: bytes = b"%PDF-1.7\nstub\n%%EOF\n",
    preview: Any = None,
    raise_exc: BaseException | None = None,
) -> MagicMock:
    fake = MagicMock()
    if raise_exc is not None:
        fake.render.pdf.side_effect = raise_exc
        fake.render.preview.side_effect = raise_exc
    else:
        fake.render.pdf.return_value = pdf
        if preview is not None:
            fake.render.preview.return_value = preview
    mocker.patch("django_poli_page.management.commands.poli_page_render.client", fake)
    return fake


def test_project_mode_writes_pdf(mocker: Any, tmp_path: Path) -> None:
    fake = _stub_client(mocker)
    output = tmp_path / "out.pdf"

    call_command(
        "poli_page_render",
        "--project=invoices",
        "--template=default",
        "--template-version=1.0.0",
        '--data={"name":"Ada"}',
        f"--output={output}",
    )

    fake.render.pdf.assert_called_once()
    call_input = fake.render.pdf.call_args[0][0]
    assert call_input["project"] == "invoices"
    assert call_input["template"] == "default"
    assert call_input["version"] == "1.0.0"
    assert call_input["data"] == {"name": "Ada"}
    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF-")


def test_inline_html_preview_mode(mocker: Any, tmp_path: Path) -> None:
    from poli_page import PreviewResult

    fake = _stub_client(
        mocker,
        preview=PreviewResult(html="<h1>Hi</h1>", total_pages=1, environment="sandbox"),
    )
    html_path = tmp_path / "in.html"
    html_path.write_text("<h1>Hi</h1>")
    output = tmp_path / "out.html"

    call_command(
        "poli_page_render",
        f"--html={html_path}",
        "--preview",
        f"--output={output}",
    )

    fake.render.preview.assert_called_once()
    assert output.exists()
    assert "<h1>Hi</h1>" in output.read_text()


def test_data_file_dash_reads_stdin(
    mocker: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = _stub_client(mocker)
    monkeypatch.setattr("sys.stdin", io.StringIO('{"k":"v"}'))
    output = tmp_path / "out.pdf"

    call_command(
        "poli_page_render",
        "--project=p",
        "--template=t",
        "--template-version=1.0.0",
        "--data-file=-",
        f"--output={output}",
    )

    call_input = fake.render.pdf.call_args[0][0]
    assert call_input["data"] == {"k": "v"}


def test_4xx_error_exits_with_code_1(mocker: Any, tmp_path: Path) -> None:
    from poli_page import BadRequestError

    err = BadRequestError(
        "bad version", code="INVALID_VERSION_FORMAT", status=400, request_id="req_1"
    )
    _stub_client(mocker, raise_exc=err)

    with pytest.raises(SystemExit) as exc_info:
        call_command(
            "poli_page_render",
            "--project=p",
            "--template=t",
            "--template-version=bad",
            f"--output={tmp_path / 'out.pdf'}",
        )
    assert exc_info.value.code == 1


def test_5xx_error_exits_with_code_2(mocker: Any, tmp_path: Path) -> None:
    from poli_page import InternalServerError

    err = InternalServerError("boom", code="INTERNAL", status=500)
    _stub_client(mocker, raise_exc=err)

    with pytest.raises(SystemExit) as exc_info:
        call_command(
            "poli_page_render",
            "--project=p",
            "--template=t",
            "--template-version=1.0.0",
            f"--output={tmp_path / 'out.pdf'}",
        )
    assert exc_info.value.code == 2


def test_connection_error_exits_with_code_3(mocker: Any, tmp_path: Path) -> None:
    from poli_page import APIConnectionError

    err = APIConnectionError("DNS failure", code="network_error")
    _stub_client(mocker, raise_exc=err)

    with pytest.raises(SystemExit) as exc_info:
        call_command(
            "poli_page_render",
            "--project=p",
            "--template=t",
            "--template-version=1.0.0",
            f"--output={tmp_path / 'out.pdf'}",
        )
    assert exc_info.value.code == 3
