# Sansible Architecture Review & Roadmap

> Review of `main` at v0.4.1 (commit `653599b`), November 2026.
> Supersedes the analysis in `REFACTORING.md` and the milestones in `ROADMAP.md`.

## Goal

Sansible is not meant to replace Ansible. It should run a well-defined subset of
Ansible — core playbook semantics plus ~30 modules — **identically to Ansible**, and
**fail loudly** on anything outside that subset. It runs natively on Windows and Linux
control nodes and needs nothing on the target beyond SSH/WinRM (and ideally `python3`
on Linux).

## Summary

The architecture is sound: an async engine, pluggable connections (local, SSH via
asyncssh, WinRM via pypsrp), a module registry, Jinja2 templating and a pure-Python
wheel. There are good building blocks: inventory parsing, pure-Python vault
decryption, a compatibility scanner, PyInstaller builds, and a golden-test harness
against `ansible-core`.

The execution engine is much weaker than the README claims. The 307 unit tests pass,
but they mostly exercise the parser and an unused second engine. The runner that
actually executes playbooks (`engine/runner.py`) has **17% coverage**, and overall
coverage is **38%**. Probe playbooks show that many features marked "✅ live tested"
either don't work or are **silently ignored**. Silent divergence is the biggest
problem: a tool like this is only useful if a playbook either behaves as it would
under Ansible or fails clearly.

## 1. Confirmed bugs

### Reproduced with probe playbooks (local connection)

| # | Problem | Location |
|---|---|---|
| 1 | Handlers never run: parsed, but `notify` does nothing | parsed at [playbook.py:321](../src/sansible/engine/playbook.py); no handler logic in the runner |
| 2 | `changed_when` / `failed_when` ignored (`failed_when: false` on a failing command still fails) | only implemented in the unused `scheduler.py` |
| 3 | `loop: "{{ my_list }}"` iterates over the characters of the string | [runner.py:634](../src/sansible/engine/runner.py), loop is never templated |
| 4 | Free-form args containing `=` lose the command (`shell: echo a=b`, `shell: echo "FOO=$FOO"`) | [playbook.py:749](../src/sansible/engine/playbook.py) |
| 5 | A block with `when: false` still runs (falsy check); a list `when: [a or b, c]` is joined without parentheses | [playbook.py:577](../src/sansible/engine/playbook.py), [:699](../src/sansible/engine/playbook.py) |
| 6 | An unreachable host exits with code **0** and shows `skipped=1` in the recap | [runner.py:717](../src/sansible/engine/runner.py) and [:417](../src/sansible/engine/runner.py) |
| 7 | `become` doesn't work: not parsed at play/task level, `HostContext.become` never set, only 10 modules call `wrap_become` | [modules/base.py:111](../src/sansible/modules/base.py) |
| 8 | `environment`, `no_log`, `until`/`retries`, `with_dict`, `run_once` are accepted and silently ignored (`no_log` printed the test secret) | `TASK_KEYWORDS` in [playbook.py:64](../src/sansible/engine/playbook.py) |
| 9 | `set_fact` / `register` override `-e` extra vars | [scheduler.py:42](../src/sansible/engine/scheduler.py) |
| 10 | Magic vars `groups`, `hostvars`, `group_names` missing; common filters (`dict2items`, …) missing | [templating.py](../src/sansible/engine/templating.py) |
| 11 | `hosts: [a, b]` crashes with a traceback | [inventory.py:351](../src/sansible/engine/inventory.py) |
| 12 | Argument validation failures print nothing in text mode | [runner.py:583](../src/sansible/engine/runner.py) |
| 13 | Package fails to import on Python 3.9 (the declared minimum) because of `str \| None` annotations | [builtin_command.py:28](../src/sansible/modules/builtin_command.py) and 9 other files |

### Found by reading the code (not executed)

- Role `defaults/` and `vars/` are loaded into `_role_vars` and never read
  ([playbook.py:425](../src/sansible/engine/playbook.py)).
- `include_tasks` resolves paths relative to the playbook, not the including file, so
  includes inside roles break ([playbook.py:483](../src/sansible/engine/playbook.py)).
- `template` doesn't search the role's `templates/` directory
  ([builtin_template.py:62](../src/sansible/modules/builtin_template.py)). Role
  `handlers/` and `files/` are not loaded either.
- Vault: `VaultLib` is initialised but never used to decrypt `vars_files`,
  `group_vars` or inline `!vault` values ([runner.py:180](../src/sansible/engine/runner.py)).
- Task-level `check_mode` is ignored, because the global flag is checked instead
  ([runner.py:593](../src/sansible/engine/runner.py)).
- `copy` in check mode always reports `changed`; `owner` and `group` are accepted and
  silently ignored ([builtin_copy.py:31](../src/sansible/modules/builtin_copy.py), [:62](../src/sansible/modules/builtin_copy.py)).
- Exceptions from per-host coroutines are dropped and the host disappears from the
  results ([runner.py:463](../src/sansible/engine/runner.py)).
- SSH ([ssh_asyncssh.py](../src/sansible/connections/ssh_asyncssh.py)):
  - `exit_status=None` (process killed by a signal) becomes rc 0.
  - `cwd` is not quoted.
  - The connection reads `ansible_ssh_timeout`, but `--timeout` sets `ansible_timeout`.
  - Connection drops are reported as rc=1 instead of unreachable.
  - No keepalive.
- Shell injection: Linux modules build commands with double quotes (`rm -rf "{path}"`
  in [builtin_file.py:93](../src/sansible/modules/builtin_file.py)), and WinRM puts
  paths and environment values into PowerShell unescaped
  ([winrm_psrp.py:159](../src/sansible/connections/winrm_psrp.py)).
- The Galaxy fallback ([galaxy/executor.py](../src/sansible/galaxy/executor.py)):
  - It needs Ansible installed on the target, which contradicts the project's premise.
  - It writes to the fixed path `/tmp/.sansible_galaxy_pb.yml`.

## 2. Structural problems

1. **There are two engines.** `PlaybookRunner` is what runs. `Scheduler` is a separate,
   mostly unused engine (only its `HostContext` is used) that contains the only
   `changed_when` implementation. There are also two inventory implementations: the
   `sansible/inventory/` package is unused. `platform/locks.py`, `tty.py`, `users.py`
   and `concurrency.py` are never referenced.
2. **The playbook is a flat task list.** Blocks become string tags (`_block_name`) on
   tasks, so nested or unnamed blocks collide, and `rescue`/`always` and inherited
   keywords can't be modelled correctly.
3. **There is no single-task execution pipeline.** `when`, loops, templating, the module
   call, `changed_when`/`failed_when`, `until`, `register` and `notify` are scattered or
   missing.
4. **Variables have no defined precedence model**, and templating is eager (play vars are
   rendered at play start) instead of happening when a value is used.
5. **Each module builds its own shell strings**, so become, quoting, check mode and diff
   behave differently from module to module.
6. **Output is `print()` calls spread through the runner.** There is no reporter
   abstraction, and ANSI colours are printed even when the output isn't a TTY.
7. **Supported-module lists are duplicated** (`SUPPORTED_MODULES`, `MODULE_ALIASES`,
   `compat_scan` tables and the registry), and they drift apart.
8. **Tooling and docs:**
   - There is no test CI; the only workflow builds binaries.
   - ruff reports ~2,900 issues and `mypy --strict` reports 173 errors.
   - The README hardcodes test counts and lab IPs.
   - `ROADMAP.md` has an AI prompt pasted into it.

## 3. Target architecture

Keep the layers. Rewrite the engine core (`runner.py`, `playbook.py` and `scheduler.py`,
about 2,200 lines), driven by tests. Keep the connections, inventory parser, vault and
most modules.

```
cli/  ──>  api.py  run_playbook(...) -> Result        (also the public Python API)
              │
engine/  loader      YAML → tree: Play → Block → Task (+ Handler), with file:line
         validator   ONE keyword/feature table, shared with compat_scan;
                     unknown or unsupported keyword = error, never ignored
         vars        explicit precedence layers + magic vars
         templar     Jinja2 NativeEnvironment, Ansible filter/test set, lazy rendering
         executor    TaskExecutor pipeline (below)
         strategy    linear (+ serial, run_once, any_errors_fatal, max_fail_percentage)
         reporter    callback interface: default text, JSON, JUnit; TTY / NO_COLOR aware
connections/   become applied once here; correct unreachable classification;
               connection pool + keepalive; ~/.ssh/config, ProxyJump
modules/       declarative argument spec; unknown args rejected; supports_check_mode;
               diff output; Ansible-shaped result keys
```

### 3.1 Task executor pipeline

For each (host, task):

```
resolve vars → evaluate when → expand loop →
  for each item: template args (omit-aware) → run module (or skip in check mode if unsupported)
                 → apply changed_when / failed_when → until/retries/delay
→ aggregate loop results → register → notify handlers (if changed) → report
```

Blocks are executed as a tree: if a task in `block` fails, run `rescue`; always run
`always`. A host that is rescued successfully is not counted as failed. Handlers run at
the end of each section (`pre_tasks`, roles + `tasks`, `post_tasks`) and on
`meta: flush_handlers`, deduplicated, and with `listen` supported.

### 3.2 Variable precedence (simplified from Ansible)

From lowest to highest:

1. role defaults
2. inventory `group_vars` (`all` → parent → child)
3. inventory host vars / `host_vars`
4. facts
5. play `vars`
6. play `vars_files`
7. role `vars`
8. block vars
9. task vars
10. include / role params
11. `set_fact` / registered vars
12. extra vars (`-e`, always wins)

Magic vars to provide: `inventory_hostname`, `inventory_hostname_short`, `groups`,
`group_names`, `hostvars`, `play_hosts` / `ansible_play_hosts`, `ansible_check_mode`,
`ansible_diff_mode`, `role_path`, `playbook_dir`, `omit`, `ansible_loop` (with 1-based
`index`).

### 3.3 Templating

- Use `jinja2.nativetypes` so `"{{ list_var }}"` stays a list. This fixes the loop bug.
- Filters: `default/d`, `mandatory`, `ternary`, `bool`, `int`, `float`, `string`,
  `to_json`, `from_json`, `to_yaml`, `from_yaml`, `to_nice_json`, `to_nice_yaml`,
  `combine`, `dict2items`, `items2dict`, `flatten`, `unique`, `union`, `intersect`,
  `difference`, `regex_search`, `regex_findall`, `regex_replace`, `quote`, `basename`,
  `dirname`, `realpath`, `expanduser`, `b64encode`, `b64decode`, `hash`, `checksum`,
  `random`, `shuffle`, `zip`, `subelements`, `split`.
- Tests: `defined`, `undefined`, `none`, `succeeded`/`success`, `failed`, `changed`,
  `skipped`, `match`, `search`, `regex`, `version`, `subset`, `superset`, `file`,
  `directory`, `exists`.
- Lookups: `file`, `env`, `pipe`, `fileglob`, `first_found`, `template`, `vars`,
  `password` (existing ones, run on the control node).

### 3.4 Become at the connection layer

Wrap the final command once, in the connection:

```
sudo -H -S -n -u USER /bin/sh -c '...'
```

with the password supplied on stdin, prompt detection, and a clear error on
"password required". Support `su` as well. File transfers with become: upload to a temp
path as the login user, then `install`/`mv` with become. Windows: `runas` through the
PSRP runspace, or leave it unsupported with an explicit error.

### 3.5 Remote helper — the single biggest correctness lever

Replace per-module shell strings with **one stdlib-only Python helper**. It is uploaded
once per host and cached by content hash under `~/.sansible/`, and invoked as
`python3 helper.py <module>` with JSON args on stdin and a JSON result on stdout.

- `file`, `copy`, `lineinfile`, `blockinfile`, `replace`, `stat`, `find`, `slurp` and the
  write side of `template` become plain Python functions on the target. That gives
  atomic writes (temp file + `os.replace`), real check mode and diffs, no quoting bugs,
  and no GNU-coreutils assumptions.
- The same functions can be unit-tested locally against `tmp_path`.
- Target compatibility: write the helper for **Python 3.6+** (RHEL 8 platform-python).
  Discover the interpreter from `ansible_python_interpreter`, then `python3`, then
  `/usr/libexec/platform-python`.
- Shell fallback only for `raw`, `command`, `shell` and `script`, or when no
  interpreter exists.
- Windows: the same pattern with one PowerShell helper (JSON in/out). Use pypsrp's
  `Client.copy()` / `Client.fetch()` instead of hand-rolled base64 chunking.

This is a simplified version of how Ansible ships modules to hosts, in roughly 300
lines, without AnsiballZ's complexity.

### 3.6 Module contract

```python
@register_module
class LineInFile(Module):
    name = "lineinfile"
    argument_spec = {
        "path": Arg(str, required=True, aliases=["dest", "destfile", "name"]),
        "state": Arg(str, default="present", choices=["present", "absent"]),
        "line": Arg(str), "regexp": Arg(str), "create": Arg(bool, default=False),
        ...
    }
    mutually_exclusive = [...]
    supports_check_mode = True
```

- Unknown arguments are an error. "Not implemented yet" arguments are an error, not
  silently dropped.
- `no_log=True` arguments are masked in all output.
- Result keys match Ansible: `changed`, `failed`, `msg`, `rc`, `stdout`,
  `stdout_lines`, `stderr`, `stderr_lines`, `diff`, `invocation`.
- The compatibility docs are **generated from the argument specs** so they can't lie.

### 3.7 Exit codes (match ansible-playbook)

| Code | Meaning |
|---|---|
| 0 | OK |
| 1 | Error |
| 2 | One or more hosts failed |
| 3 | One or more hosts unreachable |
| 4 | Parser error |
| 5 | Bad or incomplete options |
| 99 | Interrupted |
| 250 | Unexpected error |

The current codes reuse 3 and 4 with different meanings; aligning them makes CI scripts
portable between Ansible and Sansible.

## 4. Libraries

| Area | Decision |
|---|---|
| YAML / templating | **Keep** PyYAML and Jinja2; they're required for compatibility |
| SSH | **Keep** asyncssh. Use its `config=` support for `~/.ssh/config` and ProxyJump; add keepalive |
| WinRM | **Keep** pypsrp (sync API in a thread is fine); use `Client.copy/fetch` |
| Vault | Keep `cryptography` optional, with the pure-Python AES as the fallback |
| Validation / CLI / output | **Avoid** Pydantic (compiled core), Click and Rich. Use dataclasses, a small argspec validator and argparse |
| Dev | ruff (lint + format), mypy (gradual: strict per-package as packages are rewritten), pytest, pytest-asyncio, Hypothesis for parsers, Docker sshd target |
| Python | Raise the floor to **3.11** (3.9 is already broken; 3.10 reached end of life in October 2026). Shipped binaries cover old control nodes. Targets are independent (§3.5) |

## 5. Testing strategy — making "it works" provable

1. **Compare against Ansible (the main tool).** `ansible-core` is already a dev
   dependency. Run each fixture playbook with both tools over the local connection and
   compare normalised JSON (per-task changed/failed/skipped, registered vars) plus the
   resulting files on disk. Every bug in §1 would have been caught this way.
2. **Executor tests** with a `FakeConnection` that records commands and returns
   scripted results. Fast, and they cover all control flow.
3. **Module tests** that run real modules over the local connection on `ubuntu-latest`
   and `windows-latest`.
4. **Integration tests:** SSH against the sshd container (`tests/integration/docker`),
   and WinRM against localhost on the Windows runner (enable WinRM in a CI step).
5. **CI matrix:** Linux, Windows and macOS on Python 3.11–3.13, with ruff, mypy, and a
   coverage gate on `engine/` (start at 80%).
6. Every bug fix comes with a regression playbook in the comparison suite.

## 6. Features worth adding

- **Focus on the niche:** native Windows control node, plus single-file distribution
  (zipapp `sansible.pyz` alongside the PyInstaller binaries).
- **Embeddable Python API:** `sansible.run(playbook, inventory=..., extra_vars=...)`
  returning structured results. Ansible's equivalent is awkward, so this is a real gap.
- **CLIs:**
  - ad-hoc `sansible all -m ping` (currently a placeholder)
  - `sansible-inventory --list/--graph/--host`
  - `sansible-vault encrypt/decrypt/view/edit`
- **Playbook flags:** `--syntax-check`, `--list-tasks`, `--list-hosts`, `--list-tags`,
  `--start-at-task`, `--step` (the last two are accepted today but unused).
- **`compat-scan` as the authoritative pre-flight check** ("this playbook will or won't
  run, and why"), driven by the same validator table as the parser.
- **Custom modules from other packages** via a `sansible.modules` entry point.
- **`gather_facts` defaults to `true`** (to match Ansible), with fast fact gathering
  on Linux and Windows.
- **Later:** `async`/`poll` (long Windows jobs), the `free` strategy, `delegate_facts`,
  `serial`/`throttle`.

### Module tiers

Modules in **Tier 1** must be correct and run in the comparison suite:

- **Execution:** `command`, `shell`, `raw`, `script`
- **Files:** `copy`, `template`, `file`, `lineinfile`, `blockinfile`, `replace`, `stat`,
  `slurp`, `fetch`, `find`
- **Control and variables:** `debug`, `set_fact`, `assert`, `fail`, `include_vars`,
  `meta`, `add_host`, `group_by`, `setup`, `ping`
- **System:** `package`, `apt`, `dnf`/`yum`, `service`, `systemd`, `user`, `group`
- **Network:** `get_url`, `uri`, `wait_for`
- **Windows:** `win_command`, `win_shell`, `win_copy`, `win_file`, `win_stat`,
  `win_template`, `win_lineinfile`, `win_service`, `win_get_url`, `win_user`,
  `win_group`, `win_reboot`, `win_ping`, and Windows `setup`

Everything else is **experimental** and labelled as such.

## 7. What to remove

- The Galaxy executor that requires Ansible on the target. Remove it, or turn it into an
  explicit opt-in `sansible.passthrough` module.
- `engine/scheduler.py` (after its `HostContext` moves), `src/sansible/inventory/`, and
  the unused `platform/` modules.
- `docs/REFACTORING.md` and the corrupted `docs/ROADMAP.md` (replaced by this document);
  README test-count badges and lab IPs; overstated "✅ Tested" claims.

## 8. Roadmap

### Phase 0 — Stop the silent failures (~1–2 weeks)

- [ ] Fix bugs 1–13 from §1, each with a regression test
- [ ] Unsupported or unknown task/play keywords and module args are hard errors
- [ ] Honest README (what works, what doesn't)
- [ ] CI: unit tests + ruff on Linux and Windows
- [ ] Python floor 3.11; fix the 3.9-only annotation breakage either way

### Phase 1 — Core engine

- [ ] Tree model (Play → Block → Task, handlers) with file:line for errors
- [ ] TaskExecutor pipeline (§3.1), handlers, `until`/`retries`
- [ ] Variable manager with precedence + magic vars (§3.2)
- [ ] Native templating + Ansible filter/test set (§3.3)
- [ ] Become in connections (§3.4); correct unreachable handling
- [ ] Reporter interface (text / JSON); Ansible exit codes
- [ ] Comparison suite against ansible-core in CI

### Phase 2 — Modules

- [ ] Argument-spec contract (§3.6) for all Tier 1 modules
- [ ] Linux remote helper + rewrite the file-family modules on it
- [ ] Windows PowerShell helper; pypsrp copy/fetch
- [ ] Real check mode + diff; role `files/`, `templates/`, `handlers/`, `meta/` dependencies
- [ ] Vault decryption wired into vars files, inventory vars and inline `!vault`

### Phase 3 — Product

- [ ] Public Python API
- [ ] Ad-hoc, inventory and vault CLIs; list/syntax-check flags
- [ ] zipapp + binaries per release; PyPI publishing workflow
- [ ] Module entry point for third-party modules
- [ ] Generated compatibility docs

### Phase 4 — Optional

- [ ] `serial`, `run_once`, `any_errors_fatal`, `max_fail_percentage`, `throttle`
- [ ] `async`/`poll`, `free` strategy
- [ ] SSH jump hosts / `ansible_ssh_common_args` subset

## Appendix: probe used to confirm §1

Running this with `sansible-playbook -i "localhost ansible_connection=local," probe.yml -e x=2`
should print `HANDLER RAN`, `x=2`, iterate `a` and `b`, and skip the "SHOULD NOT RUN" tasks.

```yaml
- hosts: localhost
  vars: {items_var: [a, b]}
  tasks:
    - command: /bin/true
      changed_when: true
      notify: h1
    - command: /bin/false
      failed_when: false
    - debug: msg="item={{ item }}"
      loop: "{{ items_var }}"
    - shell: echo a=b
    - shell: printenv FOO
      environment: {FOO: bar}
    - set_fact: {x: 1}
    - debug: msg="x={{ x }}"
    - debug: msg="SHOULD NOT RUN"
      when: [true or false, false]
    - block:
        - debug: msg="SHOULD NOT RUN"
      when: false
  handlers:
    - name: h1
      debug: msg="HANDLER RAN"
```
