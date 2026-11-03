"""
Decide what the release workflow should do, and optionally bump the ansible-core pin.

  release_plan.py plan [--event NAME] [--tag TAG] [--core VERSION]   -> writes GitHub step outputs
  release_plan.py bump CORE_VERSION                                  -> edits pyproject.toml + __init__.py

Versioning: sansible X.Y.Z.N = ansible-core X.Y.Z + Sansible revision N. A new ansible-core
release starts at revision 1.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INIT = ROOT / "src" / "sansible" / "__init__.py"
PYPROJECT = ROOT / "pyproject.toml"


def current() -> tuple[str, str]:
    text = INIT.read_text()
    version = re.search(r'^__version__ = "([^"]+)"', text, re.M).group(1)
    core = re.search(r'^ANSIBLE_CORE_VERSION = "([^"]+)"', text, re.M).group(1)
    return version, core


def _key(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split("."))


def latest_ansible_core() -> str:
    with urllib.request.urlopen("https://pypi.org/pypi/ansible-core/json", timeout=30) as resp:
        data = json.load(resp)
    stable = [v for v, files in data["releases"].items() if re.fullmatch(r"\d+\.\d+\.\d+", v) and files
              and not all(f.get("yanked") for f in files)]
    return max(stable, key=_key)


def output(**values: str) -> None:
    lines = "".join(f"{k}={v}\n" for k, v in values.items())
    print(lines, end="")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(lines)


def plan(event: str, tag: str, core_override: str) -> None:
    version, core = current()
    if event == "push":
        if tag != f"v{version}":
            sys.exit(f"tag {tag} does not match the package version v{version}")
        output(mode="release", version=version, core=core)
        return
    target = core_override or latest_ansible_core()
    if _key(target) <= _key(core):
        output(mode="none", version=version, core=core)
        return
    output(mode="track", version=f"{target}.1", core=target)


def bump(core: str) -> None:
    version = f"{core}.1"
    init = INIT.read_text()
    init = re.sub(r'^__version__ = "[^"]+"', f'__version__ = "{version}"', init, flags=re.M)
    init = re.sub(r'^ANSIBLE_CORE_VERSION = "[^"]+"', f'ANSIBLE_CORE_VERSION = "{core}"', init, flags=re.M)
    INIT.write_text(init)
    pyproject = PYPROJECT.read_text()
    pyproject, n = re.subn(r'"ansible-core==[^"]+"', f'"ansible-core=={core}"', pyproject)
    if n != 1:
        sys.exit("could not find the ansible-core pin in pyproject.toml")
    PYPROJECT.write_text(pyproject)
    galaxy = ROOT / "src" / "ansible_collections" / "sansible" / "core" / "galaxy.yml"
    galaxy.write_text(re.sub(r"^version: .*$", f"version: {core}", galaxy.read_text(), flags=re.M))
    print(f"bumped to sansible {version} (ansible-core {core})")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--event", default=os.environ.get("GITHUB_EVENT_NAME", "workflow_dispatch"))
    p.add_argument("--tag", default=os.environ.get("GITHUB_REF_NAME", ""))
    p.add_argument("--core", default="")
    b = sub.add_parser("bump")
    b.add_argument("core")
    args = parser.parse_args()
    if args.cmd == "plan":
        plan(args.event, args.tag, args.core)
    else:
        bump(args.core)
