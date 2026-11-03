"""Load the sansible compat layer (spawn worker pool) before ansible.cli in every ansible process."""
import importlib.abc
import os
import sys

_COMPAT_ROOT = "@COMPAT_ROOT@"  # filled in by install_boot.sh (ansible-test scrubs most env vars)
os.environ.setdefault("SANSIBLE_WORKER", "pool")


class _Boot(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name == "ansible.cli" or name.startswith("ansible.executor"):
            sys.meta_path.remove(self)
            if _COMPAT_ROOT not in sys.path:
                sys.path.append(_COMPAT_ROOT)
            import compat  # noqa: F401

            if os.environ.get("SANSIBLE_BOOT_LOG"):  # proof that pool mode is active in every ansible process
                prog = os.path.basename(sys.argv[0]) if sys.argv else "?"
                with open(os.environ["SANSIBLE_BOOT_LOG"], "a") as f:
                    f.write(f"{os.getpid()} {compat.WORKER_MODEL} {prog}\n")
        return None


sys.meta_path.insert(0, _Boot())
