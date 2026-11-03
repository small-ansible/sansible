"""
Static checks for .github/workflows without running anything:
- every workflow parses as YAML
- `bash` run steps pass `bash -n`
- `pwsh` run steps parse with PowerShell's own parser, and every .NET type literal
  they use ([Some.Type]) resolves in PowerShell 7 (the shell GitHub's Windows runners use)
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPR = re.compile(r"\$\{\{.*?\}\}")

PWSH_CHECK = r"""
param([string]$Path)
$errors = $null; $tokens = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors)
$types = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.TypeExpressionAst] }, $true) |
    ForEach-Object { $_.TypeName.FullName } | Sort-Object -Unique
$unresolved = $types | Where-Object { -not ($_ -as [type]) }
@{ errors = @($errors | ForEach-Object { $_.Message }); unresolved = @($unresolved) } | ConvertTo-Json -Compress
"""


def steps():
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        doc = yaml.safe_load(wf.read_text())
        for job_name, job in (doc.get("jobs") or {}).items():
            default_shell = (job.get("defaults") or {}).get("run", {}).get("shell", "bash")
            for i, step in enumerate(job.get("steps") or []):
                if "run" in step:
                    label = f"{wf.name}:{job_name}:{step.get('name') or i}"
                    yield label, step.get("shell", default_shell), EXPR.sub("x", step["run"])


def main() -> int:
    problems = []
    pwsh = shutil.which("pwsh")
    tmp = Path(tempfile.mkdtemp(prefix="check-workflows-"))
    checker = tmp / "check.ps1"
    checker.write_text(PWSH_CHECK)
    for label, shell, script in steps():
        if shell.startswith("bash"):
            proc = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True)
            if proc.returncode:
                problems.append(f"{label}: bash: {proc.stderr.strip()}")
        elif shell == "pwsh":
            if not pwsh:
                problems.append(f"{label}: pwsh not installed, cannot check")
                continue
            step_file = tmp / "step.ps1"
            step_file.write_text(script)
            proc = subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-File", str(checker), "-Path", str(step_file)],
                                  text=True, capture_output=True)
            try:
                result = json.loads(proc.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                problems.append(f"{label}: pwsh check failed: {proc.stderr.strip() or proc.stdout.strip()}")
                continue
            problems += [f"{label}: pwsh syntax: {e}" for e in result.get("errors") or []]
            problems += [f"{label}: pwsh type does not exist: [{t}]" for t in result.get("unresolved") or []]
    shutil.rmtree(tmp, ignore_errors=True)
    for p in problems:
        print(p)
    print("workflows OK" if not problems else f"{len(problems)} workflow problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
