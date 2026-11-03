"""The installed package is wired up correctly and still matches the installed ansible-core."""
from __future__ import annotations

import subprocess
import sys
import textwrap

from conftest import IS_WINDOWS, ansible_cli, posix_only


def _python(code: str, **env: str) -> subprocess.CompletedProcess:
    import os

    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], capture_output=True, text=True,
                          env=dict(os.environ, **env), timeout=120)


def test_doctor_reports_ok():
    proc = subprocess.run([ansible_cli("sansible"), "doctor"], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.rstrip().endswith("OK"), proc.stdout


def test_pinned_ansible_core_is_installed():
    proc = _python("""
        from importlib.metadata import version
        import sansible
        assert version("ansible-core") == sansible.ANSIBLE_CORE_VERSION, (version("ansible-core"), sansible.ANSIBLE_CORE_VERSION)
        assert sansible.__version__.startswith(sansible.ANSIBLE_CORE_VERSION + "."), sansible.__version__
    """)
    assert proc.returncode == 0, proc.stderr


def test_every_source_patch_still_applies():
    proc = _python("""
        from sansible._compat import _source_patches
        problems = _source_patches.verify()
        assert not problems, problems
    """)
    assert proc.returncode == 0, proc.stderr


def test_post_import_hook_targets_exist():
    """Everything the hooks reach into must exist in this ansible-core (checked without sansible loaded)."""
    proc = _python("""
        import ansible.executor.module_common as mc
        import ansible.executor.process.worker as w
        import ansible.executor.task_queue_manager as tqm
        import ansible.module_utils._internal._debug as dbg
        import ansible.playbook.role as role
        import ansible._internal._plugins._cache as cache
        import ansible._internal._rpc_host as rpc
        import ansible.plugins.loader as loader
        from ansible.parsing.vault import VaultSecretsContext
        from ansible.utils.collection_loader import AnsibleCollectionConfig
        assert isinstance(mc.site_packages, str) and callable(mc._get_ansible_module_fqn)
        assert callable(dbg.register_for_stacktrace)
        fork_worker = getattr(w, "_ForkWorkerProcess", w.WorkerProcess)  # replaced by the pool where active
        assert hasattr(w, "WorkerQueue") and callable(fork_worker._run)
        assert callable(tqm.TaskQueueManager.cleanup)
        assert hasattr(role.Role, "_get_hash_dict")
        assert hasattr(cache, "PluginInterposer")
        assert hasattr(rpc.LocalManager, "_shared_instance") and hasattr(rpc.LocalManager, "shared_instance")
        assert callable(loader.connection_loader.get_with_context) and callable(loader.get_all_plugin_loaders)
        assert hasattr(VaultSecretsContext, "initialize")
        assert "playbook_paths" in vars(type(AnsibleCollectionConfig))
    """, **({} if IS_WINDOWS else {"SANSIBLE_DISABLE": "1"}))  # Windows can't import ansible without the layer
    assert proc.returncode == 0, proc.stderr


@posix_only  # uses SANSIBLE_DISABLE to start from a clean slate
def test_plugin_files_receive_patches():
    """ansible loads plugins with spec_from_file_location (no import hooks); patches must reach them anyway."""
    proc = _python("""
        from sansible._compat import _source_patches as sp
        sp.register({}, {"ansible.plugins.action.debug": [lambda m: setattr(m, "SANSIBLE_HOOKED", True)]})
        sp.register({}, {"ansible.plugins.loader": [sp.patch_plugin_loading]})
        sp.install()
        import sys
        from ansible.plugins.loader import action_loader, init_plugin_loader
        init_plugin_loader()
        # a builtin plugin loads as ansible_collections.ansible.builtin.plugins.<type>.<name> via its FQCN
        # (as playbooks usually name it) or as ansible.plugins.<type>.<name>; the first one wins per file
        for name in ("ansible.builtin.debug", "debug"):
            cls = action_loader.get(name, class_only=True)
            assert getattr(sys.modules[cls.__module__], "SANSIBLE_HOOKED", False), (name, cls.__module__)
    """, SANSIBLE_DISABLE="1")
    assert proc.returncode == 0, proc.stderr


def test_bundled_plugin_documentation_parses():
    """ansible parses DOCUMENTATION to build plugin options; a YAML error there fails every task at runtime."""
    for name in ("sansible.core.paramiko", "sansible.core.winlocal"):
        proc = subprocess.run([ansible_cli("ansible-doc"), "-t", "connection", "--json", name],
                              capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert '"options"' in proc.stdout, proc.stdout[:2000]


def test_bundled_collection_plugins_resolve():
    proc = _python("""
        from ansible.plugins.loader import connection_loader, init_plugin_loader
        init_plugin_loader()
        for name in ("sansible.core.paramiko", "sansible.core.winlocal"):
            assert connection_loader.has_plugin(name), name
    """)
    assert proc.returncode == 0, proc.stderr


def test_autoload_activates_on_windows_only_by_default():
    proc = _python("""
        import ansible.cli  # triggers sansible._autoload
        from sansible import _compat
        print(_compat.worker_model(), _compat.is_active())
    """)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == (["pool", "True"] if IS_WINDOWS else ["fork", "False"])


@posix_only  # on Windows ansible-core cannot import at all without the compat layer
def test_autoload_can_be_disabled():
    proc = _python("""
        import ansible.cli
        from sansible import _compat
        print(_compat.is_active())
    """, SANSIBLE_DISABLE="1", SANSIBLE_WORKER="pool")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False"
