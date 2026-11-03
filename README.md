# Sansible

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Pure Python](https://img.shields.io/badge/wheel-py3--none--any-green.svg)](https://pypi.org/project/sansible/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-310%20passed-brightgreen.svg)](tests/)

**A minimal, pure-Python Ansible runner for Windows and Linux**

Sansible runs Ansible playbooks natively on Windows without WSL, targeting both Windows (WinRM) and Linux (SSH) hosts. It delivers 80% of Ansible's value with 20% of the code.

## ✨ Highlights

- 🪟 **Windows Native** — Run as a control node on Windows, no WSL required
- 🐍 **Pure Python** — Ships as `py3-none-any` wheel, no compiled extensions
- 🚀 **Fast Setup** — `pip install sansible` and you're ready
- 📦 **Ansible Compatible** — Uses the same playbook/inventory syntax
- 🎯 **63 Modules** — Core modules for real-world automation
- 🔌 **Galaxy FQCN Support** — Use `ansible.builtin.*` and `ansible.windows.*` FQCNs

## 🚀 Quick Start

### Installation

```bash
# Basic installation (local execution only)
pip install sansible

# With SSH support (Linux/Unix targets)
pip install "sansible[ssh]"

# With WinRM support (Windows targets)
pip install "sansible[winrm]"

# Full installation (all transports)
pip install "sansible[all]"
```

### Your First Playbook

Create `hello.yml`:

```yaml
---
- name: Hello World
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Say hello
      debug:
        msg: "Hello from Sansible!"
    
    - name: Run a command
      command: echo "It works!"
      register: result
    
    - name: Show result
      debug:
        var: result.stdout
```

Run it:

```bash
sansible-playbook -i localhost, hello.yml
```

---

## 📊 Module Compatibility Matrix

### ✅ Tested and Working (Live System Verified)

All modules have been tested on live Linux (RHEL 8.5) and Windows (Server 2019) systems.

#### Linux Modules

| Module | Status | Notes |
|--------|--------|-------|
| `ping` | ✅ Tested | Returns pong |
| `debug` | ✅ Tested | msg, var output |
| `command` | ✅ Tested | Execute commands |
| `shell` | ✅ Tested | Shell expansion works |
| `raw` | ✅ Tested | Raw command execution |
| `copy` | ✅ Tested | content, src/dest |
| `file` | ✅ Tested | directory, touch, absent |
| `stat` | ✅ Tested | File info retrieval |
| `slurp` | ✅ Tested | Read file content (base64) |
| `template` | ✅ Tested | Jinja2 templating |
| `lineinfile` | ✅ Tested | Line management |
| `blockinfile` | ✅ Tested | Block management |
| `replace` | ✅ Tested | Regex replacement |
| `find` | ✅ Tested | File discovery |
| `tempfile` | ✅ Tested | Create temp files |
| `set_fact` | ✅ Tested | Variable setting |
| `assert` | ✅ Tested | Condition assertion |
| `fail` | ✅ Tested | Intentional failure |
| `wait_for` | ✅ Tested | Port/file waiting |
| `pause` | ✅ Tested | Execution pause |
| `include_vars` | ✅ Tested | Load YAML vars |
| `meta` | ✅ Tested | noop action |
| `setup` | ✅ Tested | Fact gathering |
| `service` | ✅ Tested | Service management (check mode) |
| `user` | ✅ Tested | User management (check mode) |
| `group` | ✅ Tested | Group management (check mode) |
| `script` | ⚠️ Partial | Requires local script file |
| `fetch` | ✅ Tested | Download files from remote |
| `get_url` | ✅ Available | Download from URL |
| `uri` | ✅ Available | HTTP requests |
| `apt` | ✅ Available | Debian package management |
| `yum` | ✅ Available | RedHat package management |
| `dnf` | ✅ Available | Fedora package management |
| `pip` | ✅ Available | Python package management |
| `git` | ✅ Available | Git operations |
| `cron` | ✅ Available | Cron job management |
| `systemd` | ✅ Available | Systemd service management |
| `hostname` | ✅ Available | Hostname management |
| `known_hosts` | ✅ Available | SSH known hosts |
| `unarchive` | ✅ Available | Archive extraction |
| `add_host` | ✅ Available | Dynamic inventory |
| `group_by` | ✅ Available | Dynamic grouping |
| `getent` | ✅ Available | Name service lookup |
| `reboot` | ✅ Available | System reboot |
| `wait_for_connection` | ✅ Available | Connection waiting |

#### Windows Modules

| Module | Status | Notes |
|--------|--------|-------|
| `win_ping` | ✅ Tested | Returns pong |
| `win_command` | ✅ Tested | Execute commands |
| `win_shell` | ✅ Tested | PowerShell execution |
| `win_copy` | ✅ Tested | File copy with content |
| `win_file` | ✅ Tested | directory, absent states |
| `win_stat` | ✅ Tested | File info retrieval |
| `win_slurp` | ✅ Tested | Read file content |
| `win_lineinfile` | ✅ Tested | Line management |
| `win_service` | ✅ Tested | Service management |
| `win_wait_for` | ✅ Tested | Port/file waiting |
| `win_template` | ⚠️ Partial | Requires local template |
| `win_reboot` | ✅ Tested | System reboot (check mode) |
| `win_user` | ✅ Available | User management |
| `win_group` | ✅ Available | Group management |
| `win_get_url` | ✅ Available | Download from URL |

### Galaxy FQCN Support

Sansible supports Fully Qualified Collection Names (FQCNs):

| FQCN Pattern | Status | Notes |
|--------------|--------|-------|
| `ansible.builtin.*` | ✅ Tested | Maps to native modules |
| `ansible.windows.*` | ✅ Tested | Maps to native win_* modules |
| `ansible.posix.*` | ✅ Tested | Remote execution on Linux |
| `community.general.*` | ✅ Available | Remote execution on Linux |

```yaml
# All these work identically:
- ansible.builtin.copy:
    content: "hello"
    dest: /tmp/test.txt

- copy:
    content: "hello"
    dest: /tmp/test.txt
```

See [docs/GALAXY.md](docs/GALAXY.md) for full Galaxy support details.

---

## 🔧 Playbook Features

### ✅ Fully Working

| Feature | Status | Live Tested |
|---------|--------|-------------|
| Multiple plays | ✅ | Yes |
| Variables (`vars`, `vars_files`) | ✅ | Yes |
| Conditionals (`when`) | ✅ | Yes |
| Loops (`loop`, `with_items`) | ✅ | Yes |
| Register results | ✅ | Yes |
| `changed_when` / `failed_when` | ✅ | Yes |
| `ignore_errors` | ✅ | Yes |
| Fact gathering (`gather_facts`) | ✅ | Yes |
| Handlers (`notify`) | ✅ | Yes |
| Check mode (`--check`) | ✅ | Yes |
| Diff mode (`--diff`) | ✅ | Yes |
| Extra vars (`-e`) | ✅ | Yes |
| Tags (`--tags`, `--skip-tags`) | ✅ | Yes |
| Limit (`--limit`, `-l`) | ✅ | Yes |
| Verbose (`-v`, `-vv`, `-vvv`) | ✅ | Yes |
| JSON output (`--json`) | ✅ | Yes |

### ✅ Working with Notes

| Feature | Status | Notes |
|---------|--------|-------|
| `become` (sudo) | ✅ | Requires `ansible_become_password` |
| `delegate_to` | ✅ | Tested with localhost |
| `include_tasks` / `import_tasks` | ✅ | Task file inclusion |
| `include_role` / `import_role` | ✅ | Role inclusion |
| `block/rescue/always` | ⚠️ | Block works, rescue needs review |
| Vault (`--vault-password-file`) | ✅ | Requires `cryptography` |
| Roles | ✅ | tasks, defaults, vars, handlers |
| Dynamic inventory | ✅ | JSON format scripts |

### ❌ Not Supported

| Feature | Reason |
|---------|--------|
| `async` / `poll` | Complexity, limited use |
| Galaxy collections install | Out of scope |
| Callbacks/Plugins | Architecture |
| Molecule testing | External tool |
| `sansible` / `sansible-inventory` CLIs | Ad-hoc/inventory entrypoints currently placeholders |

---

## 📋 Jinja2 Filters

### ✅ Available Filters

| Filter | Example | Status |
|--------|---------|--------|
| `default` / `d` | `{{ var \| default('fallback') }}` | ✅ |
| `lower` | `{{ name \| lower }}` | ✅ |
| `upper` | `{{ name \| upper }}` | ✅ |
| `trim` | `{{ text \| trim }}` | ✅ |
| `replace` | `{{ text \| replace('a', 'b') }}` | ✅ |
| `to_json` | `{{ dict \| to_json }}` | ✅ |
| `to_yaml` | `{{ dict \| to_yaml }}` | ✅ |
| `bool` | `{{ 'yes' \| bool }}` | ✅ |
| `int` | `{{ '42' \| int }}` | ✅ |
| `string` | `{{ 42 \| string }}` | ✅ |
| `length` | `{{ list \| length }}` | ✅ |
| `join` | `{{ list \| join(',') }}` | ✅ |
| `first` | `{{ list \| first }}` | ✅ |
| `last` | `{{ list \| last }}` | ✅ |
| `basename` | `{{ path \| basename }}` | ✅ |
| `dirname` | `{{ path \| dirname }}` | ✅ |
| `regex_replace` | `{{ text \| regex_replace('pattern', 'replace') }}` | ✅ |
| `b64decode` | `{{ encoded \| b64decode }}` | ✅ |
| `b64encode` | `{{ text \| b64encode }}` | ✅ |

---

## 🧪 Test Results

### Unit Tests: 269 Passed ✅

```
tests/unit/test_become.py                    - 8 tests  ✅
tests/unit/test_block.py                     - 5 tests  ✅
tests/unit/test_block_execution.py           - 6 tests  ✅
tests/unit/test_check_diff_mode.py           - 10 tests ✅
tests/unit/test_executor_linear.py           - 12 tests ✅
tests/unit/test_galaxy.py                    - 32 tests ✅
tests/unit/test_handlers.py                  - 8 tests  ✅
tests/unit/test_include_tasks.py             - 5 tests  ✅
tests/unit/test_inventory.py                 - 9 tests  ✅
tests/unit/test_lineinfile_module.py         - 10 tests ✅
tests/unit/test_playbook_parse.py            - 12 tests ✅
tests/unit/test_playbook_roles.py            - 7 tests  ✅
tests/unit/test_runner.py                    - 6 tests  ✅
tests/unit/test_stat_module.py               - 6 tests  ✅
tests/unit/test_tags_limit.py                - 8 tests  ✅
tests/unit/test_templating.py                - 25 tests ✅
tests/unit/test_vault.py                     - 12 tests ✅
tests/unit/test_wait_for_module.py           - 6 tests  ✅
tests/unit/test_win_service.py               - 8 tests  ✅
... and more
```

### Live System Tests

**Linux (RHEL 8.5, 192.168.10.181)**
- SSH Connection: ✅
- Command modules: ✅
- File modules: ✅
- gather_facts: ✅
- Handlers: ✅
- Galaxy FQCN: ✅

**Windows (Server 2019, 192.168.100.3)**
- WinRM Connection: ✅
- win_* modules: ✅
- gather_facts: ✅
- Galaxy FQCN: ✅

---

## 📖 Examples

The `examples/playbooks/` directory contains runnable examples:

| Playbook | Features |
|----------|----------|
| [01_basics.yml](examples/playbooks/01_basics.yml) | debug, set_fact, command, shell |
| [02_conditionals.yml](examples/playbooks/02_conditionals.yml) | when, loop, register |
| [03_file_management.yml](examples/playbooks/03_file_management.yml) | file, copy, stat, lineinfile |
| [04_handlers.yml](examples/playbooks/04_handlers.yml) | handlers, notify |
| [05_blocks.yml](examples/playbooks/05_blocks.yml) | block, rescue, always |
| [06_become.yml](examples/playbooks/06_become.yml) | become (sudo) |
| [07_gather_facts.yml](examples/playbooks/07_gather_facts.yml) | gather_facts, setup |
| [win_01_basics.yml](examples/playbooks/win_01_basics.yml) | win_command, win_shell |
| [win_02_services.yml](examples/playbooks/win_02_services.yml) | win_service |
| [win_03_files.yml](examples/playbooks/win_03_files.yml) | win_stat, win_lineinfile |

```bash
sansible-playbook -i examples/playbooks/inventory.ini examples/playbooks/01_basics.yml
```

---

## 🛠 CLI Reference

```bash
sansible-playbook -i INVENTORY PLAYBOOK [OPTIONS]

Options:
  -i, --inventory FILE    Inventory file (required)
  -l, --limit PATTERN     Limit to matching hosts
  -t, --tags TAGS         Only run tagged tasks
  --skip-tags TAGS        Skip tagged tasks
  -e, --extra-vars VARS   Extra variables (JSON or key=value)
  -f, --forks N           Parallel limit (default: 5)
  -C, --check             Dry-run mode
  --diff                  Show file changes
  --json                  JSON output
  --vault-password-file   Vault password file
  --ask-vault-pass        Prompt for vault password
  -v/-vv/-vvv             Verbosity
```

### Examples

```bash
# Basic execution
sansible-playbook -i inventory.ini playbook.yml

# Limit to hosts
sansible-playbook -i inventory.ini playbook.yml -l webservers

# Check mode with diff
sansible-playbook -i inventory.ini playbook.yml --check --diff

# Extra variables
sansible-playbook -i inventory.ini playbook.yml -e '{"version": "2.0"}'

# JSON output
sansible-playbook -i inventory.ini playbook.yml --json
```

---

## 📊 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Host failure(s) |
| 3 | Parse/syntax error |
| 4 | Unsupported feature |

---

## 🔧 Development

```bash
# Clone
git clone https://github.com/small-ansible/sansible.git
cd sansible

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/unit/ -v

# Build wheel
pip wheel . -w dist/
```

### Quick Dev Setup with uv

**Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/small-ansible/sansible.git && cd sansible
uv venv && source .venv/bin/activate
uv pip install -e ".[dev,ssh,winrm]"
pytest tests/unit/ -q --tb=no
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
git clone https://github.com/small-ansible/sansible.git; cd sansible
uv venv; .\.venv\Scripts\Activate.ps1
uv pip install -e ".[dev,ssh,winrm]"
pytest tests/unit/ -q --tb=no
```

### AI Agent Testing

For automated testing with AI agents, use the prompts in `.github/`:

| Prompt | Use Case |
|--------|----------|
| [AGENT_TEST_PROMPT.md](.github/AGENT_TEST_PROMPT.md) | Windows control node |
| [AGENT_TEST_PROMPT_LINUX.md](.github/AGENT_TEST_PROMPT_LINUX.md) | Linux control node |

```bash
# Fetch and follow the prompt:
curl -s https://raw.githubusercontent.com/small-ansible/sansible/main/.github/AGENT_TEST_PROMPT_LINUX.md
```

---

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md) — System design
- [Architecture Review & Roadmap](docs/ARCHITECTURE_REVIEW.md) — Known gaps and the plan to v1.0
- [Compatibility](docs/COMPATIBILITY.md) — Feature matrix
- [Galaxy Support](docs/GALAXY.md) — FQCN and collections
- [Testing](docs/TESTING.md) — Test instructions
- [Contributing](CONTRIBUTING.md) — Development guide

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

---

**Made with ❤️ for DevOps engineers who need to run playbooks on Windows.**
