"""`sansible` command: report how this installation is set up and whether it will work."""
from __future__ import annotations

import argparse
import os
import platform
import sys
from importlib.metadata import PackageNotFoundError, version


def _version(dist: str) -> str | None:
    try:
        return version(dist)
    except PackageNotFoundError:
        return None


def doctor() -> int:
    from sansible import ANSIBLE_CORE_VERSION, __version__
    from sansible._compat import _routing, _source_patches, install, worker_model

    problems: list[str] = []
    install()

    core = _version("ansible-core")
    print(f"sansible         {__version__}")
    print(f"ansible-core     {core or 'NOT INSTALLED'} (built for {ANSIBLE_CORE_VERSION})")
    print(f"python           {platform.python_version()} ({sys.executable})")
    print(f"platform         {platform.system()} {platform.release()} ({sys.platform})")
    print(f"worker model     {worker_model()}")
    if core is None:
        problems.append("ansible-core is not installed")
    elif core != ANSIBLE_CORE_VERSION:
        problems.append(f"ansible-core {core} differs from the tested {ANSIBLE_CORE_VERSION}")

    drift = _source_patches.verify()
    total = sum(map(len, _source_patches.all_patches().values()))
    active = sum(map(len, _source_patches.PATCHES.values()))
    print(f"source patches   {total} checked ({active} active here), "
          f"{'all apply' if not drift else f'{len(drift)} no longer apply'}")
    problems += drift

    for name, target in _routing.routes().items():
        if "." not in name:
            print(f"connection       {name} -> {target}")
    for dist, why in (("paramiko", "ssh connections from Windows"), ("pypsrp", "psrp connections to Windows")):
        print(f"{dist:<16} {_version(dist) or 'not installed'} ({why})")

    try:
        from ansible.plugins.loader import connection_loader, init_plugin_loader

        init_plugin_loader()
        if not connection_loader.has_plugin("sansible.core.paramiko"):
            problems.append("bundled collection sansible.core is not visible to ansible (collections_scan_sys_path disabled?)")
    except Exception as ex:
        problems.append(f"ansible failed to initialize: {ex}")

    for p in problems:
        print(f"PROBLEM: {p}")
    print("OK" if not problems else f"{len(problems)} problem(s) found")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    from sansible import __version__

    parser = argparse.ArgumentParser(
        prog="sansible",
        description="ansible-core that also runs natively on Windows. "
                    "Use the regular ansible commands (ansible-playbook, ansible-galaxy, ...).",
    )
    parser.add_argument("--version", action="version", version=f"sansible {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("doctor", help="check this installation (default)")
    parser.parse_args(argv)
    os.environ.setdefault("ANSIBLE_DEPRECATION_WARNINGS", "False")
    return doctor()


if __name__ == "__main__":
    sys.exit(main())
