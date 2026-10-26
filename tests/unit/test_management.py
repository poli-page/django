from __future__ import annotations

import io
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


def _stub_client(
    mocker: Any,
    *,
    pdf: bytes = b"%PDF-1.7\nstub\n%%EOF\n",
    raise_exc: BaseException | None = None,
) -> MagicMock:
    fake = MagicMock()
    if raise_exc is not None:
        fake.render.pdf.side_effect = raise_exc
    else:
        fake.render.pdf.return_value = pdf
    mocker.patch("django_poli_page.management.commands.poli_page_render.client", fake)
    return fake


def test_project_mode_writes_pdf(mocker: Any, tmp_path: Path) -> None:
    fake = _stub_client(mocker)
    output = tmp_path / "out.pdf"

    call_command(
        "poli_page_render",
        "--project=getting-started",
        "--template=welcome",
        '--data={"name":"Ada"}',
        f"--output={output}",
    )

    fake.render.pdf.assert_called_once()
    call_input = fake.render.pdf.call_args[0][0]
    assert call_input == {
        "project": "getting-started",
        "template": "welcome",
        "data": {"name": "Ada"},
    }
    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF-")


@pytest.mark.parametrize("removed", ["--template-version=1.0.0", "--preview", "--html=in.html"])
def test_removed_options_are_rejected(mocker: Any, removed: str) -> None:
    fake = _stub_client(mocker)

    with pytest.raises(CommandError, match="unrecognized arguments"):
        call_command("poli_page_render", "--project=p", "--template=t", removed)

    fake.render.pdf.assert_not_called()


@pytest.mark.parametrize("args", [["--template=t"], ["--project=p"], []])
def test_project_and_template_are_required(mocker: Any, args: list[str]) -> None:
    fake = _stub_client(mocker)

    with pytest.raises(CommandError, match="--project and --template are required"):
        call_command("poli_page_render", *args)

    fake.render.pdf.assert_not_called()


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
        "--data-file=-",
        f"--output={output}",
    )

    call_input = fake.render.pdf.call_args[0][0]
    assert call_input["data"] == {"k": "v"}


def test_4xx_error_exits_with_code_1(mocker: Any, tmp_path: Path) -> None:
    from poli_page import NotFoundError

    err = NotFoundError(
        "Template not found", code="TEMPLATE_NOT_FOUND", status=404, request_id="req_1"
    )
    _stub_client(mocker, raise_exc=err)

    with pytest.raises(SystemExit) as exc_info:
        call_command(
            "poli_page_render",
            "--project=p",
            "--template=t",
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
            f"--output={tmp_path / 'out.pdf'}",
        )
    assert exc_info.value.code == 3
