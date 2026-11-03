#!/bin/sh
# Differential test: run suite.yml under stock fork and each alternative worker model,
# record every task result with callback_plugins/record.py, and require identical output.
# Usage: PYTHON=/path/to/venv/bin/python ./compare.sh
set -eu
cd "$(dirname "$0")"
PYTHON=${PYTHON:-python3}
OUT=${OUT:-$(mktemp -d)}
mkdir -p "$OUT"
export ANSIBLE_CALLBACKS_ENABLED=record ANSIBLE_VAULT_PASSWORD_FILE=vault_pass.txt
sed -i.bak "s#^ansible_python_interpreter=.*#ansible_python_interpreter=$PYTHON#" inv.ini

run() {
    mode=$1; shift
    RECORD_FILE="$OUT/$mode.jsonl" "$@" -i inv.ini suite.yml -f 5 > "$OUT/$mode.out" 2>&1 || true
    sort "$OUT/$mode.jsonl" > "$OUT/$mode.sorted"
}

run fork "$(dirname "$PYTHON")/ansible-playbook"
run pool env COMPAT=1 SANSIBLE_WORKER=pool "$PYTHON" ../run.py
run thread env COMPAT=1 SANSIBLE_WORKER=thread "$PYTHON" ../run.py
run winsim env WINSIM=1 COMPAT=1 "$PYTHON" ../run.py

status=0
for mode in pool thread winsim; do
    if cmp -s "$OUT/fork.sorted" "$OUT/$mode.sorted"; then
        echo "$mode vs fork: identical ($(wc -l < "$OUT/$mode.sorted") records)"
    else
        echo "$mode vs fork: DIFFERENT"; diff "$OUT/fork.sorted" "$OUT/$mode.sorted" | head -20; status=1
    fi
done
mv inv.ini.bak inv.ini
exit $status
