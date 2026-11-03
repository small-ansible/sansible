# sansible.core

Bundled with the `sansible` Python package; not published to Galaxy separately.

| Plugin | Type | Purpose |
|---|---|---|
| `sansible.core.paramiko` | connection | Pure-Python SSH (paramiko). Windows controllers use it for `ssh` automatically. |
| `sansible.core.winlocal` | connection | Runs PowerShell-based modules on a Windows controller. Windows controllers use it for `local` automatically. |
