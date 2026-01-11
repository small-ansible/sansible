# Sansible — End-to-End Test Infrastructure

This directory contains everything needed to test Sansible against real Linux and Windows machines.

## Quick Start

1. **Configure your test hosts** in `test_inventory.ini`
2. **Run all tests**: `./run_all_tests.sh`

## Test Infrastructure

```
tests/e2e/
├── test_inventory.ini.template  # Copy to test_inventory.ini and fill in
├── test_inventory.ini           # Your actual hosts (gitignored)
├── run_all_tests.sh             # Main test runner
├── playbooks/
│   ├── 00_connectivity.yml      # Test all hosts are reachable
│   ├── 01_basic_modules.yml     # Test core modules
│   ├── 02_file_operations.yml   # Test file/copy/template
│   ├── 03_conditionals.yml      # Test when/loop/register
│   ├── 04_handlers.yml          # Test handlers/notify
│   ├── 05_blocks.yml            # Test block/rescue/always
│   ├── 06_become.yml            # Test privilege escalation
│   ├── 07_facts.yml             # Test gather_facts/setup
│   ├── 08_parallel.yml          # Test parallel execution
│   ├── 09_check_diff.yml        # Test --check and --diff
│   └── 10_full_scenario.yml     # Complete E2E scenario
├── golden/
│   └── compare_with_ansible.sh  # Compare Sansible vs ansible-playbook
└── results/
    └── (test outputs saved here)
```

## Prerequisites

### Linux Hosts (3 machines)
- SSH access with key-based or password auth
- Python 3 installed
- User with sudo privileges (for become tests)

### Windows Hosts (3 machines)
- WinRM enabled (run `winrm quickconfig` as admin)
- PowerShell remoting enabled
- Admin account for testing

### Control Node
```bash
pip install "sansible[all,dev]"
```

## Configuring Test Hosts

Copy the template and fill in your hosts:

```bash
cp test_inventory.ini.template test_inventory.ini
# Edit test_inventory.ini with your actual hosts
```

## Running Tests

```bash
# Run all tests
./run_all_tests.sh

# Run specific test
san run -i test_inventory.ini playbooks/01_basic_modules.yml

# Run with verbose output
./run_all_tests.sh -v

# Compare with real Ansible
./golden/compare_with_ansible.sh
```

## Test Categories

### 1. Connectivity (00_connectivity.yml)
- Verify all hosts are reachable
- Test SSH and WinRM connections

### 2. Basic Modules (01_basic_modules.yml)
- debug, set_fact, fail, assert
- command, shell, raw
- Registered variables

### 3. File Operations (02_file_operations.yml)
- copy (content and files)
- file (directory, absent)
- stat
- lineinfile
- template

### 4. Conditionals (03_conditionals.yml)
- when conditions
- loop/with_items
- changed_when, failed_when

### 5. Handlers (04_handlers.yml)
- notify
- listen
- Multiple handlers

### 6. Blocks (05_blocks.yml)
- block/rescue/always
- Nested blocks
- Error recovery

### 7. Become (06_become.yml)
- become: true
- become_user
- become_method

### 8. Facts (07_facts.yml)
- gather_facts: true
- setup module
- Conditional based on facts

### 9. Parallel Execution (08_parallel.yml)
- --forks testing
- Concurrent host execution
- Large task lists

### 10. Check/Diff (09_check_diff.yml)
- --check mode
- --diff mode
- No actual changes made

### 11. Full Scenario (10_full_scenario.yml)
- Complete deployment simulation
- All features combined
- Cleanup at end
