"""Windows-controller path handling: every patch really applies, and the patched code behaves."""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from conftest import IS_WINDOWS, windows_only

# On Linux, run under the Windows simulator, which registers the same Windows patches
SIMULATED = {} if IS_WINDOWS else {
    "PYTHONPATH": str(Path(__file__).parent / "winsim"), "SANSIBLE_TEST_WINSIM": "1", "SANSIBLE_TEST_WINSIM_FORCE": "1"}


def _python(code: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], capture_output=True, text=True, timeout=180,
                          env=dict(os.environ, **(env or {})))


@pytest.mark.skipif(not IS_WINDOWS and not sys.platform.startswith("linux"), reason="Windows, or simulated on Linux")
def test_every_windows_patch_is_applied_when_its_module_loads():
    """Registered-but-never-applied patches fail silently (plugins bypass import hooks); prove each one runs."""
    proc = _python("""
        import importlib
        from sansible._compat import _source_patches as sp

        applied = set()
        orig = sp.apply_patches
        sp.apply_patches = lambda name, source: (applied.add(name), orig(name, source))[1]

        from ansible.plugins.loader import action_loader, init_plugin_loader  # loads the compat layer
        init_plugin_loader()
        for name in sp.WINDOWS_PATCHES:
            if name.startswith("ansible.plugins.action."):
                action_loader.get("ansible.builtin." + name.rsplit(".", 1)[1], class_only=True)
            else:
                importlib.import_module(name)
        missing = sorted(set(sp.WINDOWS_PATCHES) - applied)
        assert not missing, f"registered but never applied: {missing}"
    """, SIMULATED)
    assert proc.returncode == 0, proc.stdout + proc.stderr


@windows_only
def test_copy_sends_posix_relative_paths(tmp_path):
    """Directory copies join these onto the remote destination; Windows separators would end up in file names."""
    (tmp_path / "src" / "sub" / "deeper").mkdir(parents=True)
    (tmp_path / "src" / "a.txt").write_text("a")
    (tmp_path / "src" / "sub" / "deeper" / "b.txt").write_text("b")
    proc = _python(f"""
        import os, sys
        from ansible.plugins.loader import action_loader, init_plugin_loader
        init_plugin_loader()
        mod = sys.modules[action_loader.get("ansible.builtin.copy", class_only=True).__module__]
        r = mod._walk_dirs({str(tmp_path / "src")!r} + os.sep)
        rels = [rel for _, rel in r["files"] + r["directories"]]
        assert sorted(rels) == ["a.txt", "sub", "sub/deeper", "sub/deeper/b.txt"], rels
    """)
    assert proc.returncode == 0, proc.stdout + proc.stderr
