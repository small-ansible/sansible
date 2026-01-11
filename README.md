# Sansible

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Pure Python](https://img.shields.io/badge/wheel-py3--none--any-green.svg)](https://pypi.org/project/sansible/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A minimal, pure-Python Ansible runner for Windows and Linux**

Sansible runs Ansible playbooks natively on Windows without WSL, targeting both Windows (WinRM) and Linux (SSH) hosts. It delivers 80% of Ansible's value with 20% of the code.

## ✨ Highlights

- 🪟 **Windows Native** — Run as a control node on Windows, no WSL required
- 🐍 **Pure Python** — Ships as \`py3-none-any\` wheel, no compiled extensions
- 🚀 **Fast Setup** — \`pip install sansible\` and you're ready
- 📦 **Ansible Compatible** — Uses the same playbook/inventory syntax
- 🎯 **Focused** — Core features that cover most use cases

## 🚀 Quick Start

### Installation

\`\`\`bash
# Basic installation (local execution only)
pip install sansible

# With SSH support (Linux/Unix targets)
pip install "sansible[ssh]"

# With WinRM support (Windows targets)
pip install "sansible[winrm]"

# Full installation (all transports)
pip install "sansible[all]"
\`\`\`

### Your First Playbook

Create \`hello.yml\`:

\`\`\`yaml
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
\`\`\`

Create \`inventory.ini\`:

\`\`\`ini
[local]
localhost ansible_connection=local
\`\`\`

Run it:

\`\`\`bash
san run -i inventory.ini hello.yml
\`\`\`

Output:

\`\`\`
PLAY [Hello World] ************************************************************

TASK [Say hello] **************************************************************
ok: [localhost]

TASK [Run a command] **********************************************************
changed: [localhost]

TASK [Show result] ************************************************************
ok: [localhost]

PLAY RECAP ********************************************************************
localhost                  : ok=3    changed=1    failed=0
\`\`\`

## 📖 Examples

The \`examples/playbooks/\` directory contains runnable examples for all features:

| Playbook | Features |
|----------|----------|
| [01_basics.yml](examples/playbooks/01_basics.yml) | debug, set_fact, command, shell, copy |
| [02_conditionals.yml](examples/playbooks/02_conditionals.yml) | when, loop, register, changed_when |
| [03_file_management.yml](examples/playbooks/03_file_management.yml) | file, copy, stat, lineinfile |
| [04_handlers.yml](examples/playbooks/04_handlers.yml) | handlers, notify, listen |
| [05_blocks.yml](examples/playbooks/05_blocks.yml) | block, rescue, always |
| [06_become.yml](examples/playbooks/06_become.yml) | become (sudo) |
| [07_gather_facts.yml](examples/playbooks/07_gather_facts.yml) | gather_facts, setup |
| [08_wait_for.yml](examples/playbooks/08_wait_for.yml) | wait_for (port, file) |
| [09_assert_fail.yml](examples/playbooks/09_assert_fail.yml) | assert, fail |
| [10_roles.yml](examples/playbooks/10_roles.yml) | roles |
| [11_check_diff.yml](examples/playbooks/11_check_diff.yml) | --check, --diff modes |

**Windows Examples:**

| Playbook | Features |
|----------|----------|
| [win_01_basics.yml](examples/playbooks/win_01_basics.yml) | win_command, win_shell, win_copy |
| [win_02_services.yml](examples/playbooks/win_02_services.yml) | win_service |
| [win_03_files.yml](examples/playbooks/win_03_files.yml) | win_stat, win_lineinfile |

Run any example:

\`\`\`bash
san run -i examples/playbooks/inventory.ini examples/playbooks/01_basics.yml -l localhost
\`\`\`

## 🛠 Supported Features

### Modules

| Linux | Windows | Purpose |
|-------|---------|---------|
| \`command\` | \`win_command\` | Execute command |
| \`shell\` | \`win_shell\` | Execute shell/PowerShell |
| \`copy\` | \`win_copy\` | Copy files |
| \`file\` | \`win_file\` | Manage files/directories |
| \`template\` | — | Render Jinja2 templates |
| \`stat\` | \`win_stat\` | Get file info |
| \`lineinfile\` | \`win_lineinfile\` | Manage lines in files |
| \`wait_for\` | \`win_wait_for\` | Wait for port/file |
| \`setup\` | \`setup\` | Gather facts |
| \`debug\` | \`debug\` | Print messages |
| \`set_fact\` | \`set_fact\` | Set variables |
| \`fail\` | \`fail\` | Fail with message |
| \`assert\` | \`assert\` | Assert conditions |
| — | \`win_service\` | Manage Windows services |

### Playbook Features

| Feature | Status | Notes |
|---------|--------|-------|
| Multiple plays | ✅ | Sequential execution |
| Variables (\`vars\`, \`vars_files\`) | ✅ | Full support |
| Conditionals (\`when\`) | ✅ | Jinja2 expressions |
| Loops (\`loop\`, \`with_items\`) | ✅ | List iteration |
| Handlers (\`notify\`, \`listen\`) | ✅ | Triggered on change |
| Error handling (\`block/rescue/always\`) | ✅ | Try/catch blocks |
| Privilege escalation (\`become\`) | ✅ | sudo, su |
| Fact gathering (\`gather_facts\`) | ✅ | OS info |
| Roles | ✅ | tasks, defaults, vars || `include_tasks` / `import_tasks` | ✅ | Load external tasks |
| `include_role` / `import_role` | ✅ | Dynamic role inclusion |
| `delegate_to` | ✅ | Task delegation |
| Dynamic inventory | ✅ | Executable scripts |
| Vault | ✅ | Encrypted vars (requires cryptography) || Check mode (\`--check\`) | ✅ | Dry run |
| Diff mode (\`--diff\`) | ✅ | Show changes |
| JSON output (\`--json\`) | ✅ | Machine-readable |

### Connections

| Type | Dependency | Platform |
|------|------------|----------|
| \`local\` | None | Control node |
| \`ssh\` | \`asyncssh\` | Linux/Unix |
| \`winrm\` | \`pypsrp\` | Windows |

## 📋 CLI Reference

### san run / sansible-playbook

\`\`\`bash
san run -i INVENTORY PLAYBOOK [OPTIONS]

Options:
  -i, --inventory FILE    Inventory file or directory
  -l, --limit PATTERN     Limit to hosts matching pattern
  -t, --tags TAGS         Only run tagged tasks
  --skip-tags TAGS        Skip tagged tasks
  -e, --extra-vars VARS   Extra variables (JSON or key=value)
  -f, --forks N           Parallel execution limit (default: 5)
  -C, --check             Dry-run mode (no changes)
  --diff                  Show file differences
  --json                  JSON output format
  --vault-password-file   Path to vault password file
  --ask-vault-pass        Prompt for vault password
  -v/-vv/-vvv             Verbosity level
\`\`\`

### Examples

\`\`\`bash
# Basic execution
san run -i inventory.ini playbook.yml

# Limit to specific hosts
san run -i inventory.ini playbook.yml -l webservers

# Check mode (dry run)
san run -i inventory.ini playbook.yml --check

# Show what would change
san run -i inventory.ini playbook.yml --check --diff

# Extra variables
san run -i inventory.ini playbook.yml -e "version=2.0"

# JSON output for scripting
san run -i inventory.ini playbook.yml --json
\`\`\`

## ⚠️ Not Supported

Sansible focuses on core features. These are **not supported**:

- Ansible Galaxy / Collections
- `async` / `poll`
- Callbacks / Plugins

Unsupported features raise \`UnsupportedFeatureError\` with a clear message.

## 🔧 Development

\`\`\`bash
# Clone repository
git clone https://github.com/small-ansible/sansible.git
cd sansible

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/unit/ -v

# Run a specific test
pytest tests/unit/test_become.py -v

# Build wheel
pip wheel . -w dist/

# Verify pure Python wheel
python -m tools.dep_audit
\`\`\`

## 📊 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Host failure(s) |
| 3 | Parse/syntax error |
| 4 | Unsupported feature |

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md) — System design
- [Compatibility](docs/COMPATIBILITY.md) — Feature matrix
- [Testing](docs/TESTING.md) — Test instructions
- [Contributing](docs/AI_HANDOFF.md) — Development guide

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

---

**Made with ❤️ for Windows DevOps engineers who just want to run playbooks.**
