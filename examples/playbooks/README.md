# Sansible Example Playbooks

This directory contains example playbooks demonstrating all features of Sansible.

## Quick Start

```bash
# Install Sansible
pip install sansible

# Run a basic example
san run -i inventory.ini playbooks/01_basics.yml -l localhost
```

## Playbook Index

### Linux Examples (localhost/SSH)

| File | Features Demonstrated |
|------|----------------------|
| `01_basics.yml` | debug, set_fact, command, shell, copy |
| `02_conditionals.yml` | when, loop, register, changed_when, failed_when |
| `03_file_management.yml` | file, copy, stat, lineinfile |
| `04_handlers.yml` | handlers, notify, listen |
| `05_blocks.yml` | block, rescue, always |
| `06_become.yml` | become, become_user (sudo) |
| `07_gather_facts.yml` | gather_facts, setup, ansible_facts |
| `08_wait_for.yml` | wait_for (port, file) |
| `09_assert_fail.yml` | assert, fail |
| `10_roles.yml` | role usage |
| `11_check_diff.yml` | --check and --diff modes |

### Windows Examples (WinRM)

| File | Features Demonstrated |
|------|----------------------|
| `win_01_basics.yml` | win_command, win_shell, win_copy, win_file |
| `win_02_services.yml` | win_service (start, stop, restart) |
| `win_03_files.yml` | win_stat, win_lineinfile, win_wait_for |

## Running Examples

### Local Testing (No Network Required)

```bash
# All local examples use localhost connection
san run -i playbooks/inventory.ini playbooks/01_basics.yml -l localhost
san run -i playbooks/inventory.ini playbooks/02_conditionals.yml -l localhost
san run -i playbooks/inventory.ini playbooks/03_file_management.yml -l localhost
```

### With Check Mode (Dry Run)

```bash
san run -i playbooks/inventory.ini playbooks/03_file_management.yml -l localhost --check
```

### With Diff Output

```bash
san run -i playbooks/inventory.ini playbooks/11_check_diff.yml -l localhost --diff
```

### JSON Output

```bash
san run -i playbooks/inventory.ini playbooks/01_basics.yml -l localhost --json
```

## Configuring for Real Hosts

Edit `playbooks/inventory.ini` to add your real hosts:

```ini
[linux]
webserver ansible_host=192.168.1.100 ansible_user=deploy ansible_connection=ssh

[windows]
winserver ansible_host=192.168.1.200 ansible_user=Admin ansible_connection=winrm
```

Then run:

```bash
# Linux hosts over SSH
san run -i playbooks/inventory.ini playbooks/01_basics.yml -l linux

# Windows hosts over WinRM
san run -i playbooks/inventory.ini playbooks/win_01_basics.yml -l windows
```
