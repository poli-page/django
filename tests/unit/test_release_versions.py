"""scripts/check_release_versions.py: the release's major.minor against the SDK and the contract."""

from __future__ import annotations

from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

from django_poli_page import __version__
from scripts import check_release_versions as crv

SHA = "1f705b3ce3e15ff56e2f7b8249c1a2983af2312c"
OTHER_SHA = "0eba96c1ecf9a28b7e259f444f3ca5b7c059d5fd"


@pytest.mark.parametrize(
    ("version", "minor"),
    [("0.13.0", (0, 13)), ("v0.13.4", (0, 13)), ("0.13.0rc1", (0, 13)), ("1.2.3", (1, 2))],
)
def test_release_minor(version: str, minor: tuple[int, int]) -> None:
    assert crv.release_minor(version) == minor


@pytest.mark.parametrize(
    "version", ["0.13", "bad", "v0.13.0;id", "0.13.0.1", "1!0.13.0", "0.13.0+local", ""]
)
def test_release_minor_refuses_what_is_not_x_y_z(version: str) -> None:
    with pytest.raises(crv.CheckError, match=r"is not X\.Y\.Z"):
        crv.release_minor(version)


@pytest.mark.parametrize(
    "line",
    [
        "poli-page>=0.13,<0.14",
        "poli-page>=0.13.0,<0.14",
        "poli-page >= 0.13.2, < 0.14.0",
        "poli-page<0.14,>=0.13",
        "Poli_Page>=0.13,<0.14",
    ],
)
def test_requirement_of_the_minor(line: str) -> None:
    assert crv.requirement_minor(Requirement(line)) == (0, 13)


def test_requirement_of_another_minor_is_read_as_that_minor() -> None:
    assert crv.requirement_minor(Requirement("poli-page>=0.12,<0.13")) == (0, 12)


@pytest.mark.parametrize(
    "line",
    [
        "poli-page",
        "poli-page>=0.13",
        "poli-page>=0.11.0,<2",
        "poli-page>=0.13,<1",
        "poli-page>=0.13,<0.15",
        "poli-page>=0.12,<0.14",
        "poli-page<=0.14,>=0.13",
        "poli-page~=0.13.0",
        "poli-page==0.13.*",
        "poli-page==0.13.0",
        "poli-page>=0.13,<0.14,!=0.13.1",
        "poli-page>=0.13.0rc1,<0.14",
        "poli-page>=0.13,<0.14.1",
        "poli-page>=0.13,<0.14rc1",
        "poli-page>=0.13.0.post1,<0.14",
        "poli-page[extra]>=0.13,<0.14",
        "poli-page>=0.13,<0.14; python_version < '3.12'",
    ],
)
def test_requirement_of_any_other_spelling_is_refused(line: str) -> None:
    assert crv.requirement_minor(Requirement(line)) is None


def test_the_accepted_spelling_means_every_0_13_release_and_nothing_else() -> None:
    spec = SpecifierSet(">=0.13,<0.14")

    assert [v for v in ("0.13.0", "0.13.1", "0.13.99", "0.13.1.post1") if v in spec] == [
        "0.13.0",
        "0.13.1",
        "0.13.99",
        "0.13.1.post1",
    ]
    for outside in ("0.12.9", "0.14.0", "0.14.0rc1", "0.13.0rc1", "1.0.0"):
        assert not spec.contains(outside, prereleases=True), outside


def test_stable_tags_on_the_commit() -> None:
    ls_remote = "\n".join(
        [
            f"{'a' * 40}\trefs/tags/v0.13.0",  # annotated tag object
            f"{SHA}\trefs/tags/v0.13.0^{{}}",
            f"{SHA}\trefs/tags/v0.13.0-dev.1^{{}}",
            f"{SHA}\trefs/tags/v0.12.0",  # lightweight, same commit
            f"{SHA}\trefs/tags/v0.13.0;$(touch pwned)",
            f"{SHA}\trefs/tags/x/v0.13.0",
            f"{SHA}\trefs/tags/v0.13.0.1",
            f"{SHA}\trefs/heads/v0.14.0",
            f"{OTHER_SHA}\trefs/tags/v0.11.0",
            f"{SHA}\trefs/tags/v00.13.0",
            f"{SHA}\trefs/tags/v0.013.0",
            f"{SHA}\trefs/tags/v0.13.00",
        ]
    )

    assert crv.stable_tags(ls_remote, SHA) == ["v0.12.0", "v0.13.0"]


def test_a_tag_with_leading_zeros_is_not_stable() -> None:
    with pytest.raises(crv.CheckError, match="has no stable"):
        crv.check_contract("0.13.0", (0, 13), f"{SHA}\trefs/tags/v00.13.0^{{}}", SHA)


def test_contract_of_the_minor_passes(capsys: pytest.CaptureFixture[str]) -> None:
    crv.check_contract("0.13.0", (0, 13), f"{SHA}\trefs/tags/v0.13.0^{{}}", SHA)

    assert "API contract v0.13.0 (1f705b3c) matches release v0.13.0" in capsys.readouterr().out


def test_contract_of_another_minor_names_both_versions() -> None:
    with pytest.raises(crv.CheckError) as exc_info:
        crv.check_contract("0.14.0", (0, 14), f"{SHA}\trefs/tags/v0.13.0", SHA)

    assert str(exc_info.value) == (
        "release v0.14.0 and the pinned API contract v0.13.0 (1f705b3c) differ in "
        "major.minor: pin the contract v0.14.x, or release v0.13.x"
    )


def test_contract_with_only_a_prerelease_tag_fails() -> None:
    with pytest.raises(crv.CheckError, match=r"1f705b3c has no stable vX\.Y\.Z tag"):
        crv.check_contract("0.13.0", (0, 13), f"{SHA}\trefs/tags/v0.13.0-dev.1", SHA)


# ---------------------------------------------------------------------------
# On a repository layout
# ---------------------------------------------------------------------------


def _workflow(sha_or_ref: str, comment: str = "v0.13.0") -> str:
    return (
        "jobs:\n  test:\n    steps:\n"
        "      # uses: poli-page/api-contract@not-this-one\n"
        f"      - uses: poli-page/api-contract@{sha_or_ref} # {comment}\n"
    )


def _manifest(requirement: str) -> str:
    return f'[project]\nname = "x"\ndependencies = ["django>=4.2", "{requirement}"]\n'


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "example-app").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(_manifest("poli-page>=0.13,<0.14"))
    (tmp_path / "example-app" / "pyproject.toml").write_text(_manifest("poli-page>=0.13,<0.14"))
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(_workflow(SHA))
    (tmp_path / ".github" / "workflows" / "release.yml").write_text(_workflow(SHA))
    workflows = tmp_path / ".github" / "workflows"
    monkeypatch.setattr(crv, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(crv, "WORKFLOWS", workflows)
    monkeypatch.setattr(crv, "PINNING_WORKFLOW", workflows / "ci.yml")
    tags = f"{'b' * 40}\trefs/tags/v0.13.0\n{SHA}\trefs/tags/v0.13.0^{{}}\n"
    tags += f"{OTHER_SHA}\trefs/tags/v0.12.0^{{}}\n"
    monkeypatch.setattr(crv, "list_contract_tags", lambda remote: tags)
    return tmp_path


def test_main_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert crv.main(["v0.13.0"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "poli-page>=0.13,<0.14 is required, matching release v0.13.0",
        "API contract v0.13.0 (1f705b3c) matches release v0.13.0",
    ]


def _fails(capsys: pytest.CaptureFixture[str], argv: list[str]) -> str:
    assert crv.main(argv) == 1
    return capsys.readouterr().err.strip()


def test_main_refuses_an_example_app_on_another_minor(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "example-app" / "pyproject.toml").write_text(_manifest("poli-page>=0.12,<0.13"))

    assert _fails(capsys, ["v0.13.0"]) == (
        "check-release-versions: release v0.13.0 and the required 'poli-page>=0.12,<0.13' "
        "(example-app/pyproject.toml) differ in major.minor: require poli-page>=0.13,<0.14, "
        "or release v0.12.x"
    )


def test_main_refuses_a_loose_requirement(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "pyproject.toml").write_text(_manifest("poli-page>=0.11.0,<2"))

    assert _fails(capsys, ["v0.13.0"]) == (
        "check-release-versions: release v0.13.0 needs poli-page>=0.13,<0.14, "
        "but pyproject.toml requires 'poli-page>=0.11.0,<2'"
    )


def test_main_refuses_a_missing_requirement(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "pyproject.toml").write_text('[project]\nname = "x"\ndependencies = ["django"]\n')

    assert "pyproject.toml does not require poli-page" in _fails(capsys, ["v0.13.0"])


def test_main_does_not_trust_the_pin_comment(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for name in ("ci.yml", "release.yml"):
        (repo / ".github" / "workflows" / name).write_text(_workflow(OTHER_SHA, "v0.13.0"))

    assert _fails(capsys, ["v0.13.0"]) == (
        "check-release-versions: release v0.13.0 and the pinned API contract v0.12.0 "
        "(0eba96c1) differ in major.minor: pin the contract v0.13.x, or release v0.12.x"
    )


def test_main_refuses_another_pin_in_the_release_workflow(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / ".github" / "workflows" / "release.yml").write_text(_workflow(OTHER_SHA))

    assert _fails(capsys, ["v0.13.0"]) == (
        "check-release-versions: release.yml pins the API contract 0eba96c1, but ci.yml pins "
        "1f705b3c: pin the same commit in both"
    )


def test_main_refuses_a_pin_that_is_not_a_sha(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / ".github" / "workflows" / "release.yml").write_text(_workflow("v0.13.0"))

    assert "release.yml pins the API contract at 'v0.13.0'" in _fails(capsys, ["v0.13.0"])


def test_main_refuses_a_tag_of_another_minor(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert "release v0.14.0 and the required 'poli-page>=0.13,<0.14'" in _fails(capsys, ["v0.14.0"])


def test_the_repository_requires_the_sdk_of_its_own_minor(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The real manifests, against _version.py: they move together.
    crv.check_sdk(__version__, crv.release_minor(__version__))


@pytest.mark.parametrize(
    "line",
    [
        f'      - uses: "poli-page/api-contract@{OTHER_SHA}" # v0.13.0\n',
        f"      - uses: 'poli-page/api-contract@{OTHER_SHA}'\n",
        f"        uses: poli-page/api-contract@{OTHER_SHA}\n",
    ],
    ids=["double-quoted", "single-quoted", "bare"],
)
def test_main_reads_a_quoted_pin_in_the_release_workflow(
    repo: Path, capsys: pytest.CaptureFixture[str], line: str
) -> None:
    (repo / ".github" / "workflows" / "release.yml").write_text(f"jobs:\n  x:\n    steps:\n{line}")

    assert "release.yml pins the API contract 0eba96c1, but ci.yml pins 1f705b3c" in _fails(
        capsys, ["v0.13.0"]
    )


def test_main_reads_a_quoted_pin_in_ci(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for name in ("ci.yml", "release.yml"):
        (repo / ".github" / "workflows" / name).write_text(
            f'jobs:\n  x:\n    steps:\n      - uses: "poli-page/api-contract@{SHA}"\n'
        )

    assert crv.main(["v0.13.0"]) == 0


@pytest.mark.parametrize(
    "line",
    [
        f"      - uses: \"poli-page/api-contract@{OTHER_SHA}'\n",
        f"      - {{ uses: poli-page/api-contract@{OTHER_SHA} }}\n",
    ],
    ids=["mismatched-quotes", "flow-mapping"],
)
def test_main_refuses_a_pin_it_cannot_read(
    repo: Path, capsys: pytest.CaptureFixture[str], line: str
) -> None:
    (repo / ".github" / "workflows" / "release.yml").write_text(f"jobs:\n  x:\n    steps:\n{line}")

    assert "release.yml:4: cannot read the API contract pin" in _fails(capsys, ["v0.13.0"])
