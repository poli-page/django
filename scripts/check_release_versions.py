"""A release's major.minor must be the pinned API contract's and the required poli-page SDK's.

Usage: python scripts/check_release_versions.py X.Y.Z   (or vX.Y.Z, or a PEP 440 prerelease)

django-poli-page shares its major.minor with the Poli Page API, and integration 0.N
requires the poli-page SDK 0.N.x. This script:

- fails unless pyproject.toml and example-app/pyproject.toml require poli-page as
  `>=X.Y,<X.(Y+1)` (or `>=X.Y.Z,<X.(Y+1)`) with the release's major.minor;
- reads the contract commit pinned in .github/workflows/ci.yml (never its `# vX.Y.Z`
  comment), checks that every workflow pins that same commit, lists the contract
  repository's tags, and fails unless that commit carries a stable tag vX.Y.Z with the
  release's major.minor.

Patch numbers are free. Run by the Release workflow. API_CONTRACT_REMOTE overrides the
contract repository (to check against a local one).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import Specifier
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFESTS = ("pyproject.toml", "example-app/pyproject.toml")
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
PINNING_WORKFLOW = WORKFLOWS / "ci.yml"
DEFAULT_REMOTE = "https://github.com/poli-page/api-contract.git"
SDK = "poli-page"

# `uses: poli-page/api-contract@<ref>` on a line that is not a YAML comment.
_PIN = re.compile(r"^\s*(?:-\s+)?uses:\s*poli-page/api-contract@(\S+)")
_SHA = re.compile(r"[0-9a-f]{40}")
_STABLE_TAG = re.compile(r"v([0-9]+)\.([0-9]+)\.([0-9]+)")


class CheckError(Exception):
    """A release check failed; the message says why."""


def release_minor(version: str) -> tuple[int, int]:
    """The (major, minor) of a release version `X.Y.Z` (a leading `v` and PEP 440 suffixes ok)."""
    raw = version.removeprefix("v")
    try:
        parsed = Version(raw)
    except InvalidVersion:
        parsed = None
    if parsed is None or parsed.epoch != 0 or parsed.local is not None or len(parsed.release) != 3:
        raise CheckError(f"release version '{version}' is not X.Y.Z")
    return parsed.major, parsed.minor


def sdk_requirement(manifest: Path) -> tuple[Requirement, str]:
    """The single poli-page requirement in `[project].dependencies` of a pyproject.toml.

    Returns it parsed and as written.
    """
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    found: list[tuple[Requirement, str]] = []
    for line in data.get("project", {}).get("dependencies", []):
        try:
            requirement = Requirement(line)
        except InvalidRequirement as exc:
            raise CheckError(f"{_rel(manifest)}: cannot parse '{line}': {exc}") from exc
        if canonicalize_name(requirement.name) == SDK:
            found.append((requirement, line))
    if not found:
        raise CheckError(f"{_rel(manifest)} does not require {SDK}")
    if len(found) > 1:
        raise CheckError(f"{_rel(manifest)} requires {SDK} more than once")
    return found[0]


def requirement_minor(requirement: Requirement) -> tuple[int, int] | None:
    """(X, Y) when the requirement is exactly `>=X.Y[.Z],<X.(Y+1)[.0]`, else None.

    Under PEP 440 that admits X.Y releases only: `<X.(Y+1)` also refuses the prereleases of
    X.(Y+1), and `>=X.Y` refuses those of X.Y.0.
    """
    if requirement.marker is not None or requirement.url is not None or requirement.extras:
        return None
    specifiers = list(requirement.specifier)
    lower = [s for s in specifiers if s.operator == ">="]
    upper = [s for s in specifiers if s.operator == "<"]
    if len(specifiers) != 2 or len(lower) != 1 or len(upper) != 1:
        return None
    low, high = _plain_release(lower[0]), _plain_release(upper[0])
    if low is None or high is None or len(low) not in (2, 3) or len(high) not in (2, 3):
        return None
    if len(high) == 3 and high[2] != 0:
        return None
    if high[0] != low[0] or high[1] != low[1] + 1:
        return None
    return low[0], low[1]


def stable_tags(ls_remote: str, sha: str) -> list[str]:
    """The stable `vX.Y.Z` tags on commit `sha` in `git ls-remote --tags` output, oldest first.

    An annotated tag is listed twice: its own object, then `^{}` with the commit it points at.
    A lightweight tag is listed once, with its commit. Any other tag name is ignored.
    """
    tags: set[str] = set()
    for line in ls_remote.splitlines():
        object_sha, _, ref = line.partition("\t")
        if object_sha != sha or not ref.startswith("refs/tags/"):
            continue
        name = ref.removeprefix("refs/tags/").removesuffix("^{}")
        if _STABLE_TAG.fullmatch(name):
            tags.add(name)
    return sorted(tags, key=_tag_key)


def check_sdk(version: str, minor: tuple[int, int]) -> None:
    wanted = _requirement_text(minor)
    for name in MANIFESTS:
        manifest = REPO_ROOT / name
        requirement, written = sdk_requirement(manifest)
        sdk_minor = requirement_minor(requirement)
        if sdk_minor is None:
            raise CheckError(
                f"release v{version} needs {SDK}{wanted}, but {name} requires '{written}'"
            )
        if sdk_minor != minor:
            raise CheckError(
                f"release v{version} and the required '{written}' ({name}) differ in "
                f"major.minor: require {SDK}{wanted}, or release v{_dotted(sdk_minor)}.x"
            )
    print(f"{SDK}{wanted} is required, matching release v{version}")


def pinned_contract_sha() -> str:
    """The contract commit ci.yml pins; every workflow must pin that same commit."""
    pins = _pins(PINNING_WORKFLOW)
    if not pins:
        raise CheckError("no poli-page/api-contract pin found in .github/workflows/ci.yml")
    sha = pins[0]
    for workflow in sorted(WORKFLOWS.glob("*.y*ml")):
        for pin in _pins(workflow):
            if not _SHA.fullmatch(pin):
                raise CheckError(
                    f"{workflow.name} pins the API contract at '{pin}': pin a 40-hex commit SHA"
                )
            if pin != sha:
                raise CheckError(
                    f"{workflow.name} pins the API contract {pin[:8]}, but ci.yml pins "
                    f"{sha[:8]}: pin the same commit in both"
                )
    return sha


def check_contract(version: str, minor: tuple[int, int], ls_remote: str, sha: str) -> None:
    tags = stable_tags(ls_remote, sha)
    short = sha[:8]
    if not tags:
        raise CheckError(
            f"release v{version} needs the API contract v{_dotted(minor)}.x, but the pinned "
            f"contract commit {short} has no stable vX.Y.Z tag: pin a released contract"
        )
    for tag in tags:
        if _tag_key(tag)[:2] == minor:
            print(f"API contract {tag} ({short}) matches release v{version}")
            return
    newest = _tag_key(tags[-1])[:2]
    raise CheckError(
        f"release v{version} and the pinned API contract {' '.join(tags)} ({short}) differ in "
        f"major.minor: pin the contract v{_dotted(minor)}.x, or release v{_dotted(newest)}.x"
    )


def list_contract_tags(remote: str) -> str:
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", remote],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CheckError(f"cannot list the tags of {remote}: {exc}") from exc
    return result.stdout


def main(argv: list[str]) -> int:
    try:
        if len(argv) != 1:
            raise CheckError("usage: check_release_versions.py X.Y.Z")
        version = argv[0].removeprefix("v")
        minor = release_minor(argv[0])
        check_sdk(version, minor)
        sha = pinned_contract_sha()
        remote = os.environ.get("API_CONTRACT_REMOTE") or DEFAULT_REMOTE
        check_contract(version, minor, list_contract_tags(remote), sha)
    except CheckError as exc:
        print(f"check-release-versions: {exc}", file=sys.stderr)
        return 1
    return 0


def _pins(workflow: Path) -> list[str]:
    lines = workflow.read_text(encoding="utf-8").splitlines()
    return [m.group(1) for m in map(_PIN.match, lines) if m]


def _plain_release(specifier: Specifier) -> tuple[int, ...] | None:
    """The release numbers of a specifier's version, or None if it is not a plain release."""
    if specifier.version.endswith(".*"):
        return None
    parsed = Version(specifier.version)
    if parsed.epoch or parsed.is_prerelease or parsed.is_postrelease or parsed.local:
        return None
    return parsed.release


def _tag_key(tag: str) -> tuple[int, int, int]:
    match = _STABLE_TAG.fullmatch(tag)
    assert match is not None
    return int(match[1]), int(match[2]), int(match[3])


def _requirement_text(minor: tuple[int, int]) -> str:
    return f">={_dotted(minor)},<{minor[0]}.{minor[1] + 1}"


def _dotted(minor: tuple[int, int]) -> str:
    return f"{minor[0]}.{minor[1]}"


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
