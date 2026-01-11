#!/bin/bash
# =============================================================================
# Sansible vs Ansible Compatibility Comparison
# =============================================================================
# Runs the same playbook with both Sansible and ansible-playbook, compares outputs
#
# Usage:
#   ./compare_with_ansible.sh playbook.yml
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
E2E_DIR="$(dirname "$SCRIPT_DIR")"
INVENTORY="${E2E_DIR}/test_inventory.ini"
RESULTS_DIR="${E2E_DIR}/results/golden"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$RESULTS_DIR"

# =============================================================================
# Functions
# =============================================================================

print_header() {
    echo -e "\n${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}\n"
}

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ $1${NC}"; }

compare_playbook() {
    local playbook="$1"
    local name=$(basename "$playbook" .yml)
    
    local san_json="${RESULTS_DIR}/${TIMESTAMP}_${name}_neo.json"
    local ansible_json="${RESULTS_DIR}/${TIMESTAMP}_${name}_ansible.json"
    local diff_file="${RESULTS_DIR}/${TIMESTAMP}_${name}_diff.txt"
    
    print_header "Comparing: $name"
    
    # Run with Sansible
    print_info "Running with Sansible..."
    if san run -i "$INVENTORY" --json "$playbook" > "$san_json" 2>&1; then
        print_success "Sansible completed successfully"
    else
        print_error "Sansible failed (exit code: $?)"
    fi
    
    # Run with Ansible
    print_info "Running with ansible-playbook..."
    export ANSIBLE_STDOUT_CALLBACK=json
    if ansible-playbook -i "$INVENTORY" "$playbook" > "$ansible_json" 2>&1; then
        print_success "Ansible completed successfully"
    else
        print_error "Ansible failed (exit code: $?)"
    fi
    
    # Compare results
    print_info "Comparing JSON outputs..."
    
    # Extract key fields for comparison
    python3 << EOF
import json
import sys

def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Could not load {path}: {e}")
        return None

def extract_results(data, source):
    """Extract comparable fields from Sansible or Ansible JSON output"""
    results = []
    
    if source == 'sansible':
        # Sansible format: {"plays": [{"tasks": [{"host": ..., "status": ...}]}]}
        for play in data.get('plays', []):
            for task in play.get('tasks', []):
                results.append({
                    'host': task.get('host'),
                    'task': task.get('name', 'unknown'),
                    'status': task.get('status'),
                    'changed': task.get('changed', False)
                })
    else:
        # Ansible JSON callback format
        for play in data.get('plays', []):
            for task in play.get('tasks', []):
                for host, host_data in task.get('hosts', {}).items():
                    status = 'ok'
                    if host_data.get('failed'):
                        status = 'failed'
                    elif host_data.get('skipped'):
                        status = 'skipped'
                    elif host_data.get('changed'):
                        status = 'changed'
                    
                    results.append({
                        'host': host,
                        'task': task.get('task', {}).get('name', 'unknown'),
                        'status': status,
                        'changed': host_data.get('changed', False)
                    })
    
    return results

sansible_data = load_json_safe('$san_json')
ansible_data = load_json_safe('$ansible_json')

if sansible_data and ansible_data:
    sansible_results = extract_results(sansible_data, 'sansible')
    ansible_results = extract_results(ansible_data, 'ansible')
    
    print(f"\nNeo tasks: {len(sansible_results)}")
    print(f"Ansible tasks: {len(ansible_results)}")
    
    # Compare task counts
    if len(sansible_results) == len(ansible_results):
        print("✓ Task count matches")
    else:
        print(f"✗ Task count mismatch: Sansible={len(sansible_results)}, Ansible={len(ansible_results)}")
    
    # Compare statuses
    mismatches = 0
    for i, (sansible, ansible) in enumerate(zip(sansible_results, ansible_results)):
        if san.get('status') != ansible.get('status'):
            print(f"  Task {i}: Sansible={san.get('status')}, Ansible={ansible.get('status')}")
            mismatches += 1
    
    if mismatches == 0:
        print("✓ All task statuses match")
    else:
        print(f"✗ {mismatches} status mismatches")
else:
    print("Could not perform comparison - missing data")
EOF

    echo ""
    print_info "Output files:"
    echo "  Sansible:     $san_json"
    echo "  Ansible: $ansible_json"
}

# =============================================================================
# Main
# =============================================================================

# Check for ansible-playbook
if ! command -v ansible-playbook &> /dev/null; then
    print_error "ansible-playbook not found"
    print_info "Install with: pip install ansible-core"
    exit 1
fi

# Check for san
if ! command -v san &> /dev/null; then
    print_error "san command not found"
    exit 1
fi

# Check inventory
if [[ ! -f "$INVENTORY" ]]; then
    print_error "Inventory not found: $INVENTORY"
    print_info "Copy test_inventory.ini.template to test_inventory.ini"
    exit 1
fi

# Run comparison
if [[ -n "$1" ]]; then
    # Specific playbook
    compare_playbook "$1"
else
    # Default: compare basic modules
    compare_playbook "${E2E_DIR}/playbooks/01_basic_modules.yml"
fi

print_header "Comparison Complete"
echo "Results saved in: $RESULTS_DIR"
