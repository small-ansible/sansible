# (c) 2026 Sansible contributors
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = """
    name: winlocal
    short_description: Execute on a Windows controller
    description:
        - Runs tasks on the Windows machine that runs Ansible, through local PowerShell processes.
        - "On Windows controllers Sansible routes C(local) connections here, which covers the implicit
          C(localhost) and C(delegate_to: localhost). Use PowerShell-based modules (C(ansible.windows.*))
          and controller-side actions (C(debug), C(set_fact), C(assert), ...). Python modules such as
          C(ansible.builtin.copy) need a POSIX target and do not run here."
        - Privilege escalation (become) is not supported; run Ansible from an elevated prompt instead.
    author: Sansible contributors
    version_added: "2.22.0"
    options:
      pwsh_path:
        description: PowerShell executable used to run modules.
        type: string
        default: powershell
        vars:
          - name: ansible_winlocal_pwsh_path
"""

import os
import shutil
import subprocess
import typing as t

from ansible._internal._powershell import _clixml, _script
from ansible.errors import AnsibleError, AnsibleFileNotFound
from ansible.module_utils.common.text.converters import to_bytes, to_native
from ansible.plugins.connection import ConnectionBase
from ansible.utils.display import Display

display = Display()


class Connection(ConnectionBase):
    """Local execution on a Windows controller via PowerShell."""

    transport = 'sansible.core.winlocal'
    module_implementation_preferences = ('.ps1', '.exe', '')
    allow_executable = False
    has_pipelining = True
    allow_extras = True

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        self._shell_type = 'powershell'
        super().__init__(*args, **kwargs)

    def _connect(self) -> Connection:
        if not self._connected:
            display.vvv("ESTABLISH WINDOWS LOCAL CONNECTION FOR USER: %s" % os.environ.get('USERNAME', '?'), host=self._play_context.remote_addr)
            self._connected = True
        return self

    def is_pipelining_enabled(self, wrap_async: bool = False) -> bool:
        return True

    def exec_command(self, cmd: str, in_data: bytes | None = None, sudoable: bool = True) -> tuple[int, bytes, bytes]:
        super().exec_command(cmd, in_data=in_data, sudoable=sudoable)
        if self.become:
            raise AnsibleError("become is not supported by the winlocal connection; run Ansible from an elevated prompt instead")

        # Same interpretation as the psrp plugin: the powershell shell plugin hands over either a
        # complete "powershell -EncodedCommand '...'" line (quoted for PowerShell's parser, so it
        # can't go to CreateProcess as-is) or a PowerShell script. Rebuild a real argument list.
        if enc_cmd := _script.parse_encoded_cmdline(cmd):
            script, script_args = enc_cmd
        else:
            script, script_args = f"{cmd}\nexit $LASTEXITCODE", None
        args = _script.get_pwsh_encoded_cmdline(
            script, args=script_args, pwsh_path=self.get_option('pwsh_path'), override_execution_policy=True,
        )

        display.vvv("EXEC (via local PowerShell)", host=self._play_context.remote_addr)
        proc = subprocess.run(
            args,
            input=in_data or b'',
            capture_output=True,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        return proc.returncode, proc.stdout, _clixml.replace_stderr_clixml(proc.stderr)

    def put_file(self, in_path: str, out_path: str) -> None:
        super().put_file(in_path, out_path)
        display.vvv("PUT %s TO %s" % (in_path, out_path), host=self._play_context.remote_addr)
        if not os.path.exists(to_bytes(in_path, errors='surrogate_or_strict')):
            raise AnsibleFileNotFound("file or module does not exist: %s" % to_native(in_path))
        try:
            shutil.copyfile(in_path, out_path)
        except OSError as ex:
            raise AnsibleError(f"failed to copy {in_path!r} to {out_path!r}: {ex}") from ex

    def fetch_file(self, in_path: str, out_path: str) -> None:
        super().fetch_file(in_path, out_path)
        display.vvv("FETCH %s TO %s" % (in_path, out_path), host=self._play_context.remote_addr)
        try:
            shutil.copyfile(in_path, out_path)
        except OSError as ex:
            raise AnsibleError(f"failed to copy {in_path!r} to {out_path!r}: {ex}") from ex

    def reset(self) -> None:
        pass

    def close(self) -> None:
        self._connected = False
