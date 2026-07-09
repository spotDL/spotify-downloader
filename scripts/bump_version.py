#!/usr/bin/env python3
"""Single-source version bumper for the spotDL v5 workspace (Plan 11 / CONTRACT H).

One command sets ``[project].version`` and ``__version__`` across all three
published packages (``spotdl-core``, ``spotdl-server``, ``spotdl``) so the
dependency-ordered PyPI publish (core -> server -> cli) always agrees.

It ALSO rewrites the cross-package workspace dependency pins so that the built
wheels carry an exact ``==`` requirement (``spotdl-server`` requires
``spotdl-core==<ver>``; ``spotdl`` requires ``spotdl-server==<ver>``). uv resolves
those deps from the workspace at dev time, but the *published* wheel metadata only
carries a version pin if the dependency string itself declares one -- a bare
``spotdl-core`` dependency publishes as an unpinned ``Requires-Dist: spotdl-core``,
which would let ``pip install spotdl==5.0.0`` pull an older core off PyPI. Keeping
the pins in lockstep with the version is what makes the ordered publish correct.

Usage::

    python scripts/bump_version.py 5.0.0a1     # write the version everywhere
    python scripts/bump_version.py --check      # verify every location agrees (CI guard)

``--check`` asserts all SIX version locations (3 ``[project].version`` + 3
``__version__``) AND the 2 cross-package ``==`` pins agree; it exits non-zero on any
drift so CI's ``version-consistency`` step fails on an inconsistent tree.

Refuses non-PEP-440 versions. Standard-library only (no third-party imports) so it
runs identically in CI, in a release runner, and from a bare checkout.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Canonical PEP 440 version pattern (from the PEP 440 spec / ``packaging``), inlined
# so the script has no third-party dependency. Anchored + case-insensitive + verbose.
_PEP440 = r"""
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_.]?
            (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
            [-_.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:[-_.]?(?P<post_l>post|rev|r)[-_.]?(?P<post_n2>[0-9]+)?)
        )?
        (?P<dev>                                          # dev release
            [-_.]?(?P<dev_l>dev)[-_.]?(?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?         # local version
"""
_PEP440_RE = re.compile(r"^\s*" + _PEP440 + r"\s*$", re.VERBOSE | re.IGNORECASE)


@dataclass(frozen=True)
class Package:
    """A published workspace package and the files that carry its version."""

    name: str
    pyproject: Path
    init: Path
    # Cross-package workspace deps whose ``==`` pin must track the shared version.
    workspace_deps: tuple[str, ...] = field(default_factory=tuple)


PACKAGES: tuple[Package, ...] = (
    Package(
        name="spotdl-core",
        pyproject=REPO_ROOT / "packages/core/pyproject.toml",
        init=REPO_ROOT / "packages/core/src/spotdl_core/__init__.py",
    ),
    Package(
        name="spotdl-server",
        pyproject=REPO_ROOT / "apps/server/pyproject.toml",
        init=REPO_ROOT / "apps/server/src/spotdl_server/__init__.py",
        workspace_deps=("spotdl-core",),
    ),
    Package(
        name="spotdl",
        pyproject=REPO_ROOT / "apps/cli/pyproject.toml",
        init=REPO_ROOT / "apps/cli/src/spotdl_cli/__init__.py",
        workspace_deps=("spotdl-server",),
    ),
)

_PROJECT_VERSION_RE = re.compile(r'(?m)^(?P<pre>version = ")(?P<ver>[^"]*)(?P<post>")$')
_INIT_VERSION_RE = re.compile(r'(?m)^(?P<pre>__version__ = ")(?P<ver>[^"]*)(?P<post>")$')


def _dep_pin_re(dep: str) -> re.Pattern[str]:
    """Match a dependency list entry ``"<dep>"`` or ``"<dep>==x"`` (captures the pin)."""
    return re.compile(
        r'(?m)^(?P<indent>\s*)"(?P<dep>'
        + re.escape(dep)
        + r')(?:==(?P<ver>[^"]*))?"(?P<comma>,?)\s*$'
    )


def is_pep440(version: str) -> bool:
    return _PEP440_RE.match(version) is not None


def _sub_once(pattern: re.Pattern[str], repl: str, text: str, where: str) -> str:
    new, count = pattern.subn(repl, text)
    if count != 1:
        raise SystemExit(f"error: expected exactly 1 match in {where}, found {count}")
    return new


def _set_project_version(path: Path, version: str) -> None:
    text = path.read_text(encoding="utf-8")
    repl = rf"\g<pre>{version}\g<post>"
    new = _sub_once(_PROJECT_VERSION_RE, repl, text, f"{path} [project].version")
    if new != text:
        path.write_text(new, encoding="utf-8")


def _set_init_version(path: Path, version: str) -> None:
    text = path.read_text(encoding="utf-8")
    repl = rf"\g<pre>{version}\g<post>"
    new = _sub_once(_INIT_VERSION_RE, repl, text, f"{path} __version__")
    if new != text:
        path.write_text(new, encoding="utf-8")


def _set_dep_pin(path: Path, dep: str, version: str) -> None:
    text = path.read_text(encoding="utf-8")
    repl = rf'\g<indent>"\g<dep>=={version}"\g<comma>'
    new = _sub_once(_dep_pin_re(dep), repl, text, f"{path} dep {dep!r}")
    if new != text:
        path.write_text(new, encoding="utf-8")


def _read_project_version(path: Path) -> str | None:
    m = _PROJECT_VERSION_RE.search(path.read_text(encoding="utf-8"))
    return m.group("ver") if m else None


def _read_init_version(path: Path) -> str | None:
    m = _INIT_VERSION_RE.search(path.read_text(encoding="utf-8"))
    return m.group("ver") if m else None


def _read_dep_pin(path: Path, dep: str) -> str | None:
    m = _dep_pin_re(dep).search(path.read_text(encoding="utf-8"))
    return m.group("ver") if m else None


def bump(version: str) -> None:
    if not is_pep440(version):
        raise SystemExit(f"error: {version!r} is not a valid PEP 440 version")
    for pkg in PACKAGES:
        _set_project_version(pkg.pyproject, version)
        _set_init_version(pkg.init, version)
        for dep in pkg.workspace_deps:
            _set_dep_pin(pkg.pyproject, dep, version)
    print(f"bumped all packages to {version}")


def check() -> int:
    """Return 0 if every version location agrees, else 1 (prints the discrepancies)."""
    seen: dict[str, list[str]] = {}
    problems: list[str] = []

    def record(location: str, value: str | None) -> None:
        if value is None:
            problems.append(f"  {location}: MISSING")
            return
        seen.setdefault(value, []).append(location)

    for pkg in PACKAGES:
        record(
            f"{pkg.name} [project].version ({pkg.pyproject.relative_to(REPO_ROOT)})",
            _read_project_version(pkg.pyproject),
        )
        record(
            f"{pkg.name} __version__ ({pkg.init.relative_to(REPO_ROOT)})",
            _read_init_version(pkg.init),
        )
        for dep in pkg.workspace_deps:
            record(
                f"{pkg.name} requires {dep}== ({pkg.pyproject.relative_to(REPO_ROOT)})",
                _read_dep_pin(pkg.pyproject, dep),
            )

    if len(seen) == 1 and not problems:
        (version,) = seen
        print(f"version-consistency OK: all locations at {version}")
        return 0

    print("version-consistency FAILED: locations disagree", file=sys.stderr)
    for version, locations in sorted(seen.items()):
        print(f"  {version}:", file=sys.stderr)
        for loc in locations:
            print(f"    - {loc}", file=sys.stderr)
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Set/verify the spotDL workspace version (CONTRACT H)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("version", nargs="?", help="PEP 440 version to write across all packages")
    group.add_argument("--check", action="store_true", help="verify all locations agree (CI guard)")
    args = parser.parse_args(argv)

    if args.check:
        return check()
    bump(args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
