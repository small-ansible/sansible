# Windows & Cross-Platform Compatibility Notes

This document tracks Windows-specific considerations and cross-platform compatibility issues.

## Windows Control Node Requirements

### Minimum Requirements
- Windows 10 version 1809+ or Windows Server 2019+
- Python 3.9+
- OpenSSH Client (for SSH transport)

### Optional Requirements
- WinRM enabled on target hosts (for WinRM transport)
- PowerShell 5.1+ (for certain modules)

---

## OpenSSH on Windows

### Checking Installation
```powershell
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Client*'
```

### Installing OpenSSH Client
```powershell
# As Administrator
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

### SSH Configuration Location
- Windows: `%USERPROFILE%\.ssh\config`
- Linux/macOS: `~/.ssh/config`

---

## Path Handling Differences

| Aspect | Windows | Linux/macOS |
|--------|---------|-------------|
| Separator | `\` | `/` |
| Case sensitive | No | Yes |
| Max path length | 260 (default)* | ~4096 |
| Root | `C:\`, `D:\`, etc. | `/` |
| Home directory | `%USERPROFILE%` | `~` |
| Temp directory | `%TEMP%` | `/tmp` |

*Long paths can be enabled in Windows 10+

### Enabling Long Paths (Windows)
```powershell
# As Administrator
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
    -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

---

## File Permission Differences

### Windows
- Uses ACLs (Access Control Lists)
- No direct equivalent to Unix mode bits
- Read-only flag is the only chmod-like control
- No setuid/setgid concepts

### Our Approach
- `chmod()` is best-effort on Windows
- Document which permission features work
- Avoid relying on Unix permission semantics

---

## Process Execution Differences

### Windows
- No `fork()` system call
- Uses `CreateProcess()` for new processes
- Different argument quoting rules
- Different environment variable handling

### Our Approach
- Use `subprocess.Popen` with shell=False where possible
- Custom quoting for Windows cmd.exe
- Thread-based parallelism instead of fork

---

## Signal Handling Differences

### Windows
- Only supports: SIGINT, SIGTERM, SIGABRT, SIGFPE, SIGILL, SIGSEGV
- No SIGKILL, SIGSTOP, SIGHUP, etc.
- Different signal delivery mechanism

### Our Approach
- Avoid signal-based IPC
- Use threading events for coordination
- Document signal limitations

---

## Environment Variables

| Variable | Windows | Linux |
|----------|---------|-------|
| User home | `USERPROFILE` | `HOME` |
| Username | `USERNAME` | `USER` |
| Temp dir | `TEMP` | `TMPDIR` |
| Path | `PATH` (`;` separator) | `PATH` (`:` separator) |

### Our Approach
- Abstract via `sansible.platform.users` and `sansible.platform.paths`
- Check multiple variables for home directory

---

## Line Endings

| Platform | Default |
|----------|---------|
| Windows | CRLF (`\r\n`) |
| Linux/macOS | LF (`\n`) |

### Our Approach
- Open files in text mode (Python handles conversion)
- Use `newline=''` when exact control needed
- Be explicit about line endings in templates

---

## Network Considerations

### WinRM
- Default ports: 5985 (HTTP), 5986 (HTTPS)
- Requires configuration on target hosts
- Authentication: Basic, NTLM, Kerberos

### SSH
- Default port: 22
- Windows OpenSSH client works like Unix ssh

---

## Known Issues & Workarounds

### Issue: Console Colors in Windows
**Symptom:** ANSI escape codes displayed as garbage  
**Workaround:** Detected and enabled in `platform/tty.py`

### Issue: File Locking
**Symptom:** Different APIs on Windows vs Unix  
**Workaround:** Abstracted in `platform/locks.py`

### Issue: User/Group Operations
**Symptom:** pwd/grp modules not available  
**Workaround:** Stubbed in `platform/users.py`

---

## Testing on Windows

### Setting Up Test Environment
```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install package
pip install -e ".[dev]"

# Run smoke tests
python -m tools.windows_smoke
```

### CI Testing
- GitHub Actions with `windows-latest` runner
- Test matrix: Windows 10, Windows Server 2019/2022
- Python versions: 3.9, 3.10, 3.11, 3.12

---

## Compatibility Matrix

| Feature | Windows | Linux | macOS |
|---------|---------|-------|-------|
| CLI | ✓ | ✓ | ✓ |
| Inventory parsing | ✓ | ✓ | ✓ |
| Localhost execution | ✓ | ✓ | ✓ |
| SSH transport | ✓* | ✓ | ✓ |
| WinRM transport | ✓ | ✓ | ✓ |
| File permissions | Partial | ✓ | ✓ |
| Concurrency | ✓ | ✓ | ✓ |

*Requires OpenSSH Client installed
