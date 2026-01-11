# AI Agent Prompt: Sansible v0.4.0 Testing & Debugging

## Mission
Test Sansible v0.4.0 on live Linux and Windows systems. Download binaries from GitHub, test pip installation, run playbooks against real hosts, and fix any issues found in the source code.

## Project Location
```
/home/adam/projects/sansible
```

## Live Test Systems

**Linux Target:**
- Host: `192.168.10.181`
- User: `administrator`
- Password: `Cyberark01!`
- Connection: SSH

**Windows Target:**
- Host: `192.168.100.3`
- User: `administrator`
- Password: `Cyberark01!`
- Connection: WinRM (HTTPS, port 5986)

## Phase 1: Download & Test Binaries

1. Download Linux binary from GitHub releases:
```bash
cd /tmp
curl -L -o sansible-linux https://github.com/small-ansible/sansible/releases/download/v0.4.0/sansible-linux
chmod +x sansible-linux
./sansible-linux --version
```

2. Test binary against live Linux host:
```bash
./sansible-linux -i 192.168.10.181, -u administrator -k all -m ping
# When prompted, enter password: Cyberark01!
```

## Phase 2: Test pip Installation

1. Create fresh virtual environment and install:
```bash
python -m venv /tmp/sansible-test
source /tmp/sansible-test/bin/activate
pip install sansible[all]==0.4.0
sansible --version
```

2. Create test inventory at `/tmp/test_inventory.ini`:
```ini
[linux]
linux1 ansible_host=192.168.10.181 ansible_user=administrator ansible_password=Cyberark01! ansible_connection=ssh

[windows]
win1 ansible_host=192.168.100.3 ansible_user=administrator ansible_password=Cyberark01! ansible_connection=winrm ansible_winrm_transport=ntlm ansible_winrm_server_cert_validation=ignore ansible_port=5986
```

## Phase 3: Test Playbooks

Create and run test playbook `/tmp/test_all_modules.yml`:
```yaml
---
- name: Test Linux modules
  hosts: linux
  gather_facts: true
  tasks:
    - name: Ping
      ping:

    - name: Run command
      command: hostname
      register: hostname_result

    - name: Debug output
      debug:
        var: hostname_result.stdout

    - name: Create temp file
      tempfile:
        state: file
        prefix: sansible_test_
      register: temp_file

    - name: Write to file
      copy:
        content: "Hello from Sansible v0.4.0"
        dest: "{{ temp_file.path }}"

    - name: Read file with slurp
      slurp:
        src: "{{ temp_file.path }}"
      register: file_content

    - name: Stat file
      stat:
        path: "{{ temp_file.path }}"
      register: stat_result

    - name: Add line to file
      lineinfile:
        path: "{{ temp_file.path }}"
        line: "Added by lineinfile"

    - name: Add block to file
      blockinfile:
        path: "{{ temp_file.path }}"
        block: |
          Line 1 of block
          Line 2 of block
        marker: "# {mark} SANSIBLE TEST BLOCK"

    - name: Replace text
      replace:
        path: "{{ temp_file.path }}"
        regexp: "Hello"
        replace: "Greetings"

    - name: Cleanup temp file
      file:
        path: "{{ temp_file.path }}"
        state: absent

- name: Test Windows modules
  hosts: windows
  gather_facts: true
  tasks:
    - name: Win Ping
      win_ping:

    - name: Run PowerShell command
      win_shell: hostname
      register: win_hostname

    - name: Debug Windows hostname
      debug:
        var: win_hostname.stdout

    - name: Create temp directory
      win_file:
        path: C:\Temp\sansible_test
        state: directory

    - name: Copy file to Windows
      win_copy:
        content: "Hello from Sansible on Windows"
        dest: C:\Temp\sansible_test\test.txt

    - name: Stat Windows file
      win_stat:
        path: C:\Temp\sansible_test\test.txt
      register: win_stat_result

    - name: Add line to Windows file
      win_lineinfile:
        path: C:\Temp\sansible_test\test.txt
        line: "Added by win_lineinfile"

    - name: Slurp Windows file
      win_slurp:
        src: C:\Temp\sansible_test\test.txt
      register: win_file_content

    - name: Cleanup Windows temp
      win_file:
        path: C:\Temp\sansible_test
        state: absent
```

Run the test:
```bash
sansible-playbook -i /tmp/test_inventory.ini /tmp/test_all_modules.yml -v
```

## Phase 4: Debug & Fix Issues

If any module fails:

1. Check the error message carefully
2. Look at the module source code:
   - Linux modules: `/home/adam/projects/sansible/src/sansible/modules/builtin_*.py`
   - Windows modules: `/home/adam/projects/sansible/src/sansible/modules/win_*.py`
3. Check connection handling:
   - SSH: `/home/adam/projects/sansible/src/sansible/connections/ssh_asyncssh.py`
   - WinRM: `/home/adam/projects/sansible/src/sansible/connections/winrm_psrp.py`
4. Fix the issue in source code
5. Run unit tests: `cd /home/adam/projects/sansible && pytest tests/unit/ -v`
6. Re-test against live systems

## Key Files Reference

| Component | Path |
|-----------|------|
| Module base | `src/sansible/modules/base.py` |
| Playbook parser | `src/sansible/engine/playbook.py` |
| Runner/orchestrator | `src/sansible/engine/runner.py` |
| SSH connection | `src/sansible/connections/ssh_asyncssh.py` |
| WinRM connection | `src/sansible/connections/winrm_psrp.py` |
| Scheduler | `src/sansible/engine/scheduler.py` |

## Module Pattern
All modules follow this pattern:
```python
@register_module
class MyModule(Module):
    name = "my_module"
    required_args = ["required_param"]
    optional_args = {"optional_param": "default_value"}
    
    async def run(self) -> ModuleResult:
        # Use self.connection.run(), self.connection.put(), self.connection.stat()
        return ModuleResult(changed=True, msg="done")
```

## Success Criteria
- [ ] Binary downloads and runs
- [ ] `pip install sansible[all]` works
- [ ] Linux ping/command/copy/file/template modules work
- [ ] Windows win_ping/win_shell/win_copy/win_file modules work
- [ ] gather_facts works on both platforms
- [ ] All 237 unit tests pass
- [ ] No connection errors

## After Fixes
If you fix any issues:
```bash
cd /home/adam/projects/sansible
pytest tests/unit/ -v  # Run tests
git add -A && git commit -m "Fix: <description>"
git push origin main
```
