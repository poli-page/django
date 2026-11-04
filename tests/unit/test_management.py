from __future__ import annotations

import io
import os
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
    # The command writes with the SDK's render_to_file(), which streams the PDF.
    fake = MagicMock()
    if raise_exc is not None:
        fake.render.pdf_stream.side_effect = raise_exc
    else:
        fake.render.pdf_stream.return_value.__enter__.return_value = iter([pdf[:4], pdf[4:]])
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

    fake.render.pdf_stream.assert_called_once()
    call_input = fake.render.pdf_stream.call_args[0][0]
    assert call_input == {
        "project": "getting-started",
        "template": "welcome",
        "data": {"name": "Ada"},
    }
    assert output.read_bytes() == b"%PDF-1.7\nstub\n%%EOF\n"


@pytest.mark.parametrize("removed", ["--template-version=1.0.0", "--preview", "--html=in.html"])
def test_removed_options_are_rejected(mocker: Any, removed: str) -> None:
    fake = _stub_client(mocker)

    with pytest.raises(CommandError, match="unrecognized arguments"):
        call_command("poli_page_render", "--project=p", "--template=t", removed)

    fake.render.pdf_stream.assert_not_called()


@pytest.mark.parametrize("args", [["--template=t"], ["--project=p"], []])
def test_project_and_template_are_required(mocker: Any, args: list[str]) -> None:
    fake = _stub_client(mocker)

    with pytest.raises(CommandError, match="--project and --template are required"):
        call_command("poli_page_render", *args)

    fake.render.pdf_stream.assert_not_called()


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

    call_input = fake.render.pdf_stream.call_args[0][0]
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


def test_invalid_response_exits_with_code_4(mocker: Any, tmp_path: Path) -> None:
    # A 2xx whose body is not JSON (a proxy, a captive portal): not an API status error,
    # not a connection error, so the generic code. The message names the code.
    from poli_page import InvalidResponseError

    err = InvalidResponseError(
        "Invalid response: HTTP 200 body is not JSON",
        code="invalid_response",
        status=200,
        request_id="req_proxy",
    )
    _stub_client(mocker, raise_exc=err)
    stderr = io.StringIO()

    with pytest.raises(SystemExit) as exc_info:
        call_command(
            "poli_page_render",
            "--project=p",
            "--template=t",
            f"--output={tmp_path / 'out.pdf'}",
            stderr=stderr,
        )
    assert exc_info.value.code == 4
    assert "code=invalid_response" in stderr.getvalue()
    assert not (tmp_path / "out.pdf").exists()


def test_reports_the_written_size(mocker: Any, tmp_path: Path) -> None:
    _stub_client(mocker)
    output = tmp_path / "nested" / "out.pdf"
    stdout = io.StringIO()

    call_command(
        "poli_page_render", "--project=p", "--template=t", f"--output={output}", stdout=stdout
    )

    assert "Rendered 20 bytes in " in stdout.getvalue()
    assert f"Wrote to {output}." in stdout.getvalue()


def _run_with_bad_target(mocker: Any, output: Path) -> tuple[MagicMock, int | str | None, str]:
    fake = _stub_client(mocker)
    stderr = io.StringIO()
    with pytest.raises(SystemExit) as exc_info:
        call_command(
            "poli_page_render", "--project=p", "--template=t", f"--output={output}", stderr=stderr
        )
    return fake, exc_info.value.code, stderr.getvalue()


def test_directory_target_is_refused_before_the_render(mocker: Any, tmp_path: Path) -> None:
    fake, code, stderr = _run_with_bad_target(mocker, tmp_path)

    assert code == 4
    assert "code=io_error" in stderr
    fake.render.pdf_stream.assert_not_called()


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write a read-only file")
def test_read_only_target_is_refused_before_the_render(mocker: Any, tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    output.write_bytes(b"old")
    output.chmod(0o444)

    fake, code, stderr = _run_with_bad_target(mocker, output)

    assert code == 4
    assert "code=io_error" in stderr
    fake.render.pdf_stream.assert_not_called()
    assert output.read_bytes() == b"old"


def test_failed_render_leaves_the_target_as_it_was(mocker: Any, tmp_path: Path) -> None:
    from poli_page import InternalServerError

    output = tmp_path / "out.pdf"
    output.write_bytes(b"old")
    _stub_client(mocker, raise_exc=InternalServerError("boom", code="INTERNAL", status=500))

    with pytest.raises(SystemExit):
        call_command("poli_page_render", "--project=p", "--template=t", f"--output={output}")

    assert output.read_bytes() == b"old"
    assert [p.name for p in tmp_path.iterdir()] == ["out.pdf"]
