# Sansible Supported Modules

> **Total**: 61 modules (45 Linux + 16 Windows)  
> **Version**: 0.4.0

## Linux Modules (45)

All modules support `ansible.builtin.*` FQCN syntax.

### Core Command Modules

| Module | Description | Status |
|--------|-------------|--------|
| `ping` | Test connectivity | ✅ Tested |
| `command` | Execute commands | ✅ Tested |
| `shell` | Execute shell commands with pipes | ✅ Tested |
| `raw` | Execute raw commands (no Python) | ✅ Tested |
| `script` | Transfer and execute local script | ✅ Tested |

### File Management

| Module | Description | Status |
|--------|-------------|--------|
| `file` | Manage files and directories | ✅ Tested |
| `copy` | Copy content or files | ✅ Tested |
| `template` | Jinja2 template rendering | ✅ Tested |
| `lineinfile` | Manage lines in files | ✅ Tested |
| `blockinfile` | Manage blocks in files | ✅ Tested |
| `replace` | Regex replacement | ✅ Tested |
| `stat` | Get file information | ✅ Tested |
| `slurp` | Read file content (base64) | ✅ Tested |
| `fetch` | Download files from remote | ✅ Tested |
| `find` | Find files matching criteria | ✅ Tested |
| `tempfile` | Create temporary files | ✅ Tested |
| `unarchive` | Extract archives | ✅ Available |

### Variables & Facts

| Module | Description | Status |
|--------|-------------|--------|
| `debug` | Print debug messages | ✅ Tested |
| `set_fact` | Set host facts | ✅ Tested |
| `setup` | Gather system facts | ✅ Tested |
| `include_vars` | Load variables from YAML | ✅ Tested |

### Control Flow

| Module | Description | Status |
|--------|-------------|--------|
| `assert` | Verify conditions | ✅ Tested |
| `fail` | Intentionally fail | ✅ Tested |
| `pause` | Pause execution | ✅ Tested |
| `meta` | Meta actions (noop, flush_handlers) | ✅ Tested |
| `wait_for` | Wait for port/file/condition | ✅ Tested |
| `wait_for_connection` | Wait for connection | ✅ Available |

### System Management

| Module | Description | Status |
|--------|-------------|--------|
| `hostname` | Manage hostname | ✅ Tested |
| `service` | Manage services (sysvinit) | ✅ Tested |
| `systemd` | Manage systemd services | ✅ Tested |
| `cron` | Manage cron jobs | ✅ Tested |
| `reboot` | Reboot systems | ✅ Available |

### User & Group

| Module | Description | Status |
|--------|-------------|--------|
| `user` | Manage users | ✅ Tested |
| `group` | Manage groups | ✅ Tested |
| `getent` | Query name service databases | ✅ Tested |

### Package Management

| Module | Description | Status |
|--------|-------------|--------|
| `package` | Generic package manager | ✅ Tested |
| `apt` | Debian/Ubuntu packages | ✅ Available |
| `yum` | RHEL/CentOS packages | ✅ Tested |
| `dnf` | Fedora packages | ✅ Available |
| `pip` | Python packages | ✅ Tested |

### Network

| Module | Description | Status |
|--------|-------------|--------|
| `uri` | HTTP requests | ✅ Tested |
| `get_url` | Download files from URL | ✅ Available |
| `known_hosts` | Manage SSH known hosts | ✅ Tested |

### Source Control

| Module | Description | Status |
|--------|-------------|--------|
| `git` | Git operations | ✅ Available |

### Inventory

| Module | Description | Status |
|--------|-------------|--------|
| `add_host` | Add host to inventory | ✅ Available |
| `group_by` | Create groups dynamically | ✅ Available |

---

## Windows Modules (16)

All modules support `ansible.windows.*` FQCN syntax.

### Core Command Modules

| Module | Description | Status |
|--------|-------------|--------|
| `win_ping` | Test connectivity | ✅ Tested |
| `win_command` | Execute CMD commands | ✅ Tested |
| `win_shell` | Execute PowerShell commands | ✅ Tested |

### File Management

| Module | Description | Status |
|--------|-------------|--------|
| `win_file` | Manage files and directories | ✅ Tested |
| `win_copy` | Copy content or files | ✅ Tested |
| `win_template` | Jinja2 template rendering | ✅ Available |
| `win_lineinfile` | Manage lines in files | ✅ Tested |
| `win_stat` | Get file information | ✅ Tested |
| `win_slurp` | Read file content (base64) | ✅ Tested |

### System Management

| Module | Description | Status |
|--------|-------------|--------|
| `win_service` | Manage Windows services | ✅ Tested |
| `win_hostname` | Manage hostname | ✅ Tested |
| `win_reboot` | Reboot Windows systems | ✅ Tested |
| `win_wait_for` | Wait for port/file | ✅ Tested |

### User & Group

| Module | Description | Status |
|--------|-------------|--------|
| `win_user` | Manage Windows users | ✅ Tested |
| `win_group` | Manage Windows groups | ✅ Tested |

### Network

| Module | Description | Status |
|--------|-------------|--------|
| `win_get_url` | Download files from URL | ✅ Tested |

---

## Module Status Legend

| Status | Meaning |
|--------|---------|
| ✅ Tested | Verified on production systems |
| ✅ Available | Implemented, basic testing |
| ⚠️ Partial | Some features not implemented |
| ❌ Missing | Not yet implemented |

---

## FQCN Support

Sansible automatically normalizes Fully Qualified Collection Names:

```yaml
# These are equivalent:
- ansible.builtin.copy:
    src: /tmp/foo
    dest: /tmp/bar

- copy:
    src: /tmp/foo
    dest: /tmp/bar
```

Supported namespaces:
- `ansible.builtin.*` → Linux modules
- `ansible.windows.*` → Windows modules
- `community.general.*` → Partial support

---

## Out of Scope

These features are intentionally not implemented:

| Feature | Reason |
|---------|--------|
| `async` / `poll` | Complexity, rarely used |
| Galaxy collections | External dependencies |
| Complex lookups | Complexity |
| Vault encrypt | Only decrypt supported |
| Callbacks/Plugins | Architecture decision |
