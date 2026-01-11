# Windows Agent Prompt — Sansible Full Cycle Testing

Copy-paste the prompt below into your AI agent on Windows.

---

## PROMPT START

You are a development agent for **Sansible**, a pure-Python Ansible runner. Your task is to perform the complete Windows development cycle: download, test, fix bugs, update documentation, and verify the executable.

### Project Info

- **GitHub Repo**: https://github.com/small-ansible/sansible
- **Project Philosophy**: Minimal pure-Python Ansible runner (no compiled extensions, Windows-native control node)
- **Current Version**: 0.4.0

### Live Test Systems

Use these systems for testing. Both are accessible from this Windows machine:

```ini
[linux]
linux1 ansible_host=192.168.10.181 ansible_user=administrator ansible_password=Cyberark01! ansible_become_password=Cyberark01!

[windows]
win1 ansible_host=192.168.100.3 ansible_user=administrator ansible_password=Cyberark01! ansible_connection=winrm ansible_winrm_transport=ntlm ansible_winrm_server_cert_validation=ignore ansible_port=5985
```

Save this as `C:\temp\test_inventory.ini` for testing.

---

### PHASE 1: Setup & Download

1. **Clone or update the repository:**
   ```powershell
   cd C:\projects
   if (Test-Path sansible) { 
       cd sansible; git pull origin main 
   } else { 
       git clone https://github.com/small-ansible/sansible.git; cd sansible 
   }
   ```

2. **Create virtual environment and install:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev,ssh,winrm]"
   ```

3. **Verify installation:**
   ```powershell
   san --version
   sansible-playbook --version
   ```

---

### PHASE 2: Run Unit Tests

Run all unit tests (no network required):

```powershell
pytest tests/unit/ -v --tb=short
```

**Expected**: All 269+ tests should pass. If any fail, fix them before proceeding.

---

### PHASE 3: Test Python Version Against Live Systems

#### 3.1 Create Linux Test Playbook

Save as `C:\temp\test_all_linux.yml`:

```yaml
---
- name: Test All Linux Modules
  hosts: linux
  gather_facts: no
  become: yes
  vars:
    test_results: {}

  tasks:
    # === URI ===
    - name: Test uri module
      uri:
        url: https://httpbin.org/get
        method: GET
        return_content: no
      register: uri_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'uri': 'OK' if uri_result is not failed else 'FAILED'}) }}"

    # === GET_URL ===
    - name: Test get_url module
      get_url:
        url: https://www.google.com/robots.txt
        dest: /tmp/test_robots.txt
        mode: '0644'
      register: get_url_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'get_url': 'OK' if get_url_result is not failed else 'FAILED'}) }}"

    # === YUM ===
    - name: Test yum module (check mode)
      yum:
        name: htop
        state: present
      check_mode: yes
      register: yum_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'yum': 'OK' if yum_result is not failed else 'FAILED'}) }}"

    # === DNF ===
    - name: Test dnf module (check mode)
      dnf:
        name: vim
        state: present
      check_mode: yes
      register: dnf_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'dnf': 'OK' if dnf_result is not failed else 'FAILED'}) }}"

    # === PIP ===
    - name: Test pip module (check mode)
      pip:
        name: requests
        state: present
      check_mode: yes
      register: pip_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'pip': 'OK' if pip_result is not failed else 'FAILED'}) }}"

    # === GIT ===
    - name: Test git module (check mode)
      git:
        repo: https://github.com/small-ansible/sansible.git
        dest: /tmp/sansible_test
      check_mode: yes
      register: git_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'git': 'OK' if git_result is not failed else 'FAILED'}) }}"

    # === CRON ===
    - name: Test cron module
      cron:
        name: "test_cron_job"
        minute: "0"
        hour: "5"
        job: "/bin/echo hello"
        state: absent
      register: cron_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'cron': 'OK' if cron_result is not failed else 'FAILED'}) }}"

    # === SYSTEMD ===
    - name: Test systemd module
      systemd:
        name: sshd
        state: started
      check_mode: yes
      register: systemd_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'systemd': 'OK' if systemd_result is not failed else 'FAILED'}) }}"

    # === HOSTNAME ===
    - name: Test hostname module (check mode)
      hostname:
        name: "{{ ansible_host }}"
      check_mode: yes
      register: hostname_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'hostname': 'OK' if hostname_result is not failed else 'FAILED'}) }}"

    # === KNOWN_HOSTS ===
    - name: Test known_hosts module
      known_hosts:
        name: github.com
        key: "github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl"
        path: /tmp/test_known_hosts
        state: present
      register: known_hosts_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'known_hosts': 'OK' if known_hosts_result is not failed else 'FAILED'}) }}"

    # === UNARCHIVE ===
    - name: Create test archive first
      shell: echo "test" > /tmp/test_file.txt && tar czf /tmp/test_archive.tar.gz -C /tmp test_file.txt
      ignore_errors: yes
    - name: Test unarchive module
      unarchive:
        src: /tmp/test_archive.tar.gz
        dest: /tmp/unarchive_test/
        remote_src: yes
      register: unarchive_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'unarchive': 'OK' if unarchive_result is not failed else 'FAILED'}) }}"

    # === ADD_HOST ===
    - name: Test add_host module
      add_host:
        name: dynamic_host_1
        groups: dynamic_group
        ansible_host: 192.168.1.100
      register: add_host_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'add_host': 'OK' if add_host_result is not failed else 'FAILED'}) }}"

    # === GROUP_BY ===
    - name: Test group_by module
      group_by:
        key: "os_family_test"
      register: group_by_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'group_by': 'OK' if group_by_result is not failed else 'FAILED'}) }}"

    # === GETENT ===
    - name: Test getent module
      getent:
        database: passwd
        key: root
      register: getent_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'getent': 'OK' if getent_result is not failed else 'FAILED'}) }}"

    # === WAIT_FOR_CONNECTION ===
    - name: Test wait_for_connection module
      wait_for_connection:
        timeout: 5
      register: wait_for_connection_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'wait_for_connection': 'OK' if wait_for_connection_result is not failed else 'FAILED'}) }}"

    # === REBOOT ===
    - name: Test reboot module (check mode only)
      reboot:
        reboot_timeout: 60
      check_mode: yes
      register: reboot_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'reboot': 'OK' if reboot_result is not failed else 'FAILED'}) }}"

    # === SERVICE ===
    - name: Test service module
      service:
        name: sshd
        state: started
      check_mode: yes
      register: service_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'service': 'OK' if service_result is not failed else 'FAILED'}) }}"

    # === USER ===
    - name: Test user module (check mode)
      user:
        name: testuser_sansible
        state: present
        comment: "Test user for sansible"
      check_mode: yes
      register: user_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'user': 'OK' if user_result is not failed else 'FAILED'}) }}"

    # === GROUP ===
    - name: Test group module (check mode)
      group:
        name: testgroup_sansible
        state: present
      check_mode: yes
      register: group_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'group': 'OK' if group_result is not failed else 'FAILED'}) }}"

    # === SUMMARY ===
    - name: "========== LINUX TEST SUMMARY =========="
      debug:
        msg: |
          === LINUX MODULES TEST RESULTS ===
          uri:                 {{ test_results.uri | default('NOT RUN') }}
          get_url:             {{ test_results.get_url | default('NOT RUN') }}
          yum:                 {{ test_results.yum | default('NOT RUN') }}
          dnf:                 {{ test_results.dnf | default('NOT RUN') }}
          pip:                 {{ test_results.pip | default('NOT RUN') }}
          git:                 {{ test_results.git | default('NOT RUN') }}
          cron:                {{ test_results.cron | default('NOT RUN') }}
          systemd:             {{ test_results.systemd | default('NOT RUN') }}
          hostname:            {{ test_results.hostname | default('NOT RUN') }}
          known_hosts:         {{ test_results.known_hosts | default('NOT RUN') }}
          unarchive:           {{ test_results.unarchive | default('NOT RUN') }}
          add_host:            {{ test_results.add_host | default('NOT RUN') }}
          group_by:            {{ test_results.group_by | default('NOT RUN') }}
          getent:              {{ test_results.getent | default('NOT RUN') }}
          wait_for_connection: {{ test_results.wait_for_connection | default('NOT RUN') }}
          reboot:              {{ test_results.reboot | default('NOT RUN') }}
          service:             {{ test_results.service | default('NOT RUN') }}
          user:                {{ test_results.user | default('NOT RUN') }}
          group:               {{ test_results.group | default('NOT RUN') }}
```

#### 3.2 Create Windows Test Playbook

Save as `C:\temp\test_all_windows.yml`:

```yaml
---
- name: Test All Windows Modules
  hosts: windows
  gather_facts: no
  vars:
    test_results: {}

  tasks:
    # === WIN_PING ===
    - name: Test win_ping module
      win_ping:
      register: win_ping_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_ping': 'OK' if win_ping_result is not failed else 'FAILED'}) }}"

    # === WIN_COMMAND ===
    - name: Test win_command module
      win_command: whoami
      register: win_command_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_command': 'OK' if win_command_result is not failed else 'FAILED'}) }}"

    # === WIN_SHELL ===
    - name: Test win_shell module
      win_shell: Get-Date
      register: win_shell_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_shell': 'OK' if win_shell_result is not failed else 'FAILED'}) }}"

    # === WIN_COPY ===
    - name: Test win_copy module
      win_copy:
        content: "Test content from sansible"
        dest: C:\temp\sansible_test.txt
      register: win_copy_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_copy': 'OK' if win_copy_result is not failed else 'FAILED'}) }}"

    # === WIN_STAT ===
    - name: Test win_stat module
      win_stat:
        path: C:\Windows\System32\cmd.exe
      register: win_stat_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_stat': 'OK' if win_stat_result is not failed else 'FAILED'}) }}"

    # === WIN_SLURP ===
    - name: Test win_slurp module
      win_slurp:
        src: C:\temp\sansible_test.txt
      register: win_slurp_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_slurp': 'OK' if win_slurp_result is not failed else 'FAILED'}) }}"

    # === WIN_LINEINFILE ===
    - name: Test win_lineinfile module
      win_lineinfile:
        path: C:\temp\sansible_test.txt
        line: "Added by win_lineinfile test"
        create: yes
      register: win_lineinfile_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_lineinfile': 'OK' if win_lineinfile_result is not failed else 'FAILED'}) }}"

    # === WIN_SERVICE ===
    - name: Test win_service module
      win_service:
        name: Spooler
        state: started
      check_mode: yes
      register: win_service_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_service': 'OK' if win_service_result is not failed else 'FAILED'}) }}"

    # === WIN_WAIT_FOR ===
    - name: Test win_wait_for module (port)
      win_wait_for:
        port: 5985
        host: 127.0.0.1
        timeout: 5
      register: win_wait_for_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_wait_for': 'OK' if win_wait_for_result is not failed else 'FAILED'}) }}"

    # === WIN_USER ===
    - name: Test win_user module (check mode)
      win_user:
        name: sansible_testuser
        password: TempPass123!
        state: present
      check_mode: yes
      register: win_user_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_user': 'OK' if win_user_result is not failed else 'FAILED'}) }}"

    # === WIN_GROUP ===
    - name: Test win_group module (check mode)
      win_group:
        name: sansible_testgroup
        state: present
      check_mode: yes
      register: win_group_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_group': 'OK' if win_group_result is not failed else 'FAILED'}) }}"

    # === WIN_REBOOT ===
    - name: Test win_reboot module (check mode only)
      win_reboot:
        reboot_timeout: 60
      check_mode: yes
      register: win_reboot_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_reboot': 'OK' if win_reboot_result is not failed else 'FAILED'}) }}"

    # === WIN_GET_URL ===
    - name: Test win_get_url module
      win_get_url:
        url: https://www.google.com/robots.txt
        dest: C:\temp\robots.txt
      register: win_get_url_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_get_url': 'OK' if win_get_url_result is not failed else 'FAILED'}) }}"

    # === WIN_HOSTNAME ===
    - name: Test win_hostname module (check mode)
      win_hostname:
        name: "{{ ansible_host }}"
      check_mode: yes
      register: win_hostname_result
      ignore_errors: yes
    - set_fact:
        test_results: "{{ test_results | combine({'win_hostname': 'OK' if win_hostname_result is not failed else 'FAILED'}) }}"

    # === SUMMARY ===
    - name: "========== WINDOWS TEST SUMMARY =========="
      debug:
        msg: |
          === WINDOWS MODULES TEST RESULTS ===
          win_ping:        {{ test_results.win_ping | default('NOT RUN') }}
          win_command:     {{ test_results.win_command | default('NOT RUN') }}
          win_shell:       {{ test_results.win_shell | default('NOT RUN') }}
          win_copy:        {{ test_results.win_copy | default('NOT RUN') }}
          win_stat:        {{ test_results.win_stat | default('NOT RUN') }}
          win_slurp:       {{ test_results.win_slurp | default('NOT RUN') }}
          win_lineinfile:  {{ test_results.win_lineinfile | default('NOT RUN') }}
          win_service:     {{ test_results.win_service | default('NOT RUN') }}
          win_wait_for:    {{ test_results.win_wait_for | default('NOT RUN') }}
          win_user:        {{ test_results.win_user | default('NOT RUN') }}
          win_group:       {{ test_results.win_group | default('NOT RUN') }}
          win_reboot:      {{ test_results.win_reboot | default('NOT RUN') }}
          win_get_url:     {{ test_results.win_get_url | default('NOT RUN') }}
          win_hostname:    {{ test_results.win_hostname | default('NOT RUN') }}
```

#### 3.3 Run Tests with Python

```powershell
# Test Linux modules
sansible-playbook -i C:\temp\test_inventory.ini C:\temp\test_all_linux.yml -v

# Test Windows modules
sansible-playbook -i C:\temp\test_inventory.ini C:\temp\test_all_windows.yml -v
```

**Expected**: All modules should show "OK" in the summary.

---

### PHASE 4: Download and Test Windows Executable

#### 4.1 Download Latest Release from GitHub Actions

```powershell
# Get latest successful run
$runs = gh api repos/small-ansible/sansible/actions/runs --jq '.workflow_runs[] | select(.conclusion=="success") | {id: .id, name: .name}' | ConvertFrom-Json
$latestRun = $runs | Select-Object -First 1

# List artifacts
gh api repos/small-ansible/sansible/actions/runs/$($latestRun.id)/artifacts

# Download Windows artifact (replace ARTIFACT_ID with actual ID)
$artifactId = "REPLACE_WITH_ARTIFACT_ID"
gh api repos/small-ansible/sansible/actions/artifacts/$artifactId/zip > C:\temp\sansible_artifact.zip

# Extract
Expand-Archive -Path C:\temp\sansible_artifact.zip -DestinationPath C:\temp\sansible_exe -Force
cd C:\temp\sansible_exe
Expand-Archive -Path *.zip -DestinationPath . -Force
```

#### 4.2 Verify Executable

```powershell
cd C:\temp\sansible_exe
.\sansible.exe --version
.\sansible-playbook.exe --version
```

#### 4.3 Run Tests with Executable

```powershell
# Test Linux modules with exe
.\sansible-playbook.exe -i C:\temp\test_inventory.ini C:\temp\test_all_linux.yml -v

# Test Windows modules with exe
.\sansible-playbook.exe -i C:\temp\test_inventory.ini C:\temp\test_all_windows.yml -v
```

---

### PHASE 5: Troubleshooting

If any tests fail, follow this process:

1. **Get detailed error output:**
   ```powershell
   sansible-playbook -i C:\temp\test_inventory.ini C:\temp\test_all_linux.yml -vvv 2>&1 | Tee-Object -FilePath C:\temp\debug.log
   ```

2. **Check specific module:**
   ```powershell
   # Create a minimal test playbook for the failing module
   # Example for git module:
   @"
   ---
   - hosts: linux
     tasks:
       - name: Debug git module
         git:
           repo: https://github.com/small-ansible/sansible.git
           dest: /tmp/test_git
         check_mode: yes
   "@ | Out-File -FilePath C:\temp\test_single.yml -Encoding utf8
   
   sansible-playbook -i C:\temp\test_inventory.ini C:\temp\test_single.yml -vvv
   ```

3. **Run unit tests for specific module:**
   ```powershell
   pytest tests/unit/test_<module_name>.py -v
   ```

4. **Fix the issue in the source code** (see docs/AI_HANDOFF.md for architecture)

5. **Re-run unit tests to verify fix:**
   ```powershell
   pytest tests/unit/ -v
   ```

6. **Re-test against live systems**

---

### PHASE 6: Update Documentation

After all tests pass, update the compatibility documentation:

1. **Read current COMPATIBILITY.md:**
   ```powershell
   Get-Content docs\COMPATIBILITY.md
   ```

2. **Update L/W columns** to reflect what was tested:
   - `L` = Tested on Linux
   - `W` = Tested on Windows
   - `L/W` = Tested on both

3. **Update STATUS.md** if any new features were added

4. **Commit and push:**
   ```powershell
   git add -A
   git commit -m "docs: Update compatibility after Windows testing"
   git push origin main
   ```

---

### PHASE 7: Verification Checklist

Before considering the cycle complete, verify:

- [ ] All 269+ unit tests pass
- [ ] All 19 Linux modules pass (Python version)
- [ ] All 14 Windows modules pass (Python version)
- [ ] All 19 Linux modules pass (exe version)
- [ ] All 14 Windows modules pass (exe version)
- [ ] COMPATIBILITY.md updated with L/W columns
- [ ] Changes committed and pushed
- [ ] GitHub Actions build succeeds

---

### Key Files Reference

| File | Purpose |
|------|---------|
| `src/sansible/engine/runner.py` | Main orchestrator, task execution |
| `src/sansible/engine/playbook.py` | YAML parsing, Task dataclass |
| `src/sansible/modules/builtin_*.py` | Linux modules |
| `src/sansible/modules/win_*.py` | Windows modules |
| `src/sansible/connections/winrm_psrp.py` | WinRM connection |
| `src/sansible/connections/ssh_asyncssh.py` | SSH connection |
| `docs/COMPATIBILITY.md` | Module compatibility matrix |
| `docs/agent/STATUS.md` | Implementation status |

### Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| `ignore_errors` not working | Check `runner.py` line ~316, ensure `and not task.ignore_errors` |
| Task-level `check_mode` ignored | Ensure `check_mode` field in Task dataclass and parsing in playbook.py |
| `NoneType` has no attribute | Module likely not handling None stat result |
| WinRM connection failed | Verify `ansible_winrm_transport=ntlm` and port 5985 open |
| SSH connection failed | Verify `asyncssh` installed: `pip install sansible[ssh]` |

---

## PROMPT END

---

*Last updated: 2026-01-11*
*Tested on: Linux RHEL 8.5, Windows Server 2019*
