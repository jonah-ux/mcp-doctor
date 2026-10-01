"""Reject a release tag that does not identify this exact package and checkout."""

import argparse
import re
import subprocess
import tomllib
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, stderr=subprocess.PIPE
    ).strip()


def validate(repo: Path, tag: str) -> None:
    """Require an annotated vMAJOR.MINOR.PATCH tag matching package and HEAD."""
    if not re.fullmatch(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", tag):
        raise ValueError("release tag must be vMAJOR.MINOR.PATCH without leading zeroes")
    with (repo / "pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    if tag != f"v{version}":
        raise ValueError("release tag does not match project.version")
    ref = f"refs/tags/{tag}"
    if git(repo, "cat-file", "-t", ref) != "tag":
        raise ValueError("release tag must be annotated")
    if git(repo, "rev-parse", f"{ref}^{{}}") != git(repo, "rev-parse", "HEAD"):
        raise ValueError("release tag does not identify the checked-out HEAD")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        validate(args.repo, args.tag)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Release refused: {exc}\n")
    print(f"Release identity verified: {args.tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
