#!/bin/bash
# =============================================================================
# Sansible — End-to-End Test Runner
# =============================================================================
# Run all E2E tests with a single command
#
# Usage:
#   ./run_all_tests.sh                 # Run all tests
#   ./run_all_tests.sh -v              # Verbose mode
#   ./run_all_tests.sh --quick         # Quick connectivity test only
#   ./run_all_tests.sh --playbook 01   # Run specific playbook
#   ./run_all_tests.sh --compare       # Compare Sansible vs Ansible
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INVENTORY="${SCRIPT_DIR}/test_inventory.ini"
PLAYBOOKS_DIR="${SCRIPT_DIR}/playbooks"
RESULTS_DIR="${SCRIPT_DIR}/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default settings
VERBOSE=""
FORKS=5
QUICK_MODE=false
COMPARE_MODE=false
SPECIFIC_PLAYBOOK=""
JSON_OUTPUT=false

# =============================================================================
# Functions
# =============================================================================

print_header() {
    echo -e "\n${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

usage() {
    cat << EOF
Sansible E2E Test Runner

Usage: $0 [OPTIONS]

Options:
    -h, --help          Show this help message
    -v, --verbose       Enable verbose output
    -q, --quick         Run only connectivity test (fast)
    -p, --playbook NUM  Run specific playbook (e.g., 01, 02, 03)
    -f, --forks NUM     Number of parallel forks (default: 5)
    -c, --compare       Compare Sansible output with ansible-playbook
    -j, --json          Output results in JSON format
    --check             Run in check mode (dry-run)
    --diff              Show diffs for file changes

Examples:
    $0                       # Run all tests
    $0 --quick               # Quick connectivity check
    $0 --playbook 01         # Run 01_basic_modules.yml only
    $0 --compare             # Compare with real Ansible
    $0 -v --forks 10         # Verbose with 10 parallel connections

EOF
    exit 0
}

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check san command
    if command -v san &> /dev/null; then
        print_success "san command found"
    else
        print_error "san command not found. Install with: pip install sansible"
        exit 1
    fi
    
    # Check inventory file
    if [[ -f "$INVENTORY" ]]; then
        print_success "Inventory file found: $INVENTORY"
    else
        print_error "Inventory file not found: $INVENTORY"
        print_info "Copy test_inventory.ini.template to test_inventory.ini and configure your hosts"
        exit 1
    fi
    
    # Check playbooks directory
    if [[ -d "$PLAYBOOKS_DIR" ]]; then
        PLAYBOOK_COUNT=$(ls -1 "$PLAYBOOKS_DIR"/*.yml 2>/dev/null | wc -l)
        print_success "Playbooks directory found: $PLAYBOOK_COUNT playbooks"
    else
        print_error "Playbooks directory not found: $PLAYBOOKS_DIR"
        exit 1
    fi
    
    # Create results directory
    mkdir -p "$RESULTS_DIR"
    print_success "Results directory: $RESULTS_DIR"
    
    # Check if ansible-playbook is available (for comparison)
    if $COMPARE_MODE; then
        if command -v ansible-playbook &> /dev/null; then
            print_success "ansible-playbook found (for comparison)"
        else
            print_warning "ansible-playbook not found - comparison mode disabled"
            COMPARE_MODE=false
        fi
    fi
}

run_playbook() {
    local playbook="$1"
    local playbook_name=$(basename "$playbook" .yml)
    local result_file="${RESULTS_DIR}/${TIMESTAMP}_${playbook_name}.log"
    local json_file="${RESULTS_DIR}/${TIMESTAMP}_${playbook_name}.json"
    
    print_info "Running: $playbook_name"
    
    local cmd="san run -i $INVENTORY"
    
    # Add options
    [[ -n "$VERBOSE" ]] && cmd="$cmd -v"
    cmd="$cmd --forks $FORKS"
    [[ "$CHECK_MODE" == "true" ]] && cmd="$cmd --check"
    [[ "$DIFF_MODE" == "true" ]] && cmd="$cmd --diff"
    [[ "$JSON_OUTPUT" == "true" ]] && cmd="$cmd --json"
    
    cmd="$cmd $playbook"
    
    # Run and capture output
    if $JSON_OUTPUT; then
        if eval "$cmd" > "$json_file" 2>&1; then
            print_success "$playbook_name passed"
            return 0
        else
            print_error "$playbook_name failed (see $json_file)"
            return 1
        fi
    else
        if eval "$cmd" 2>&1 | tee "$result_file"; then
            print_success "$playbook_name passed"
            return 0
        else
            print_error "$playbook_name failed (see $result_file)"
            return 1
        fi
    fi
}

run_all_tests() {
    print_header "Running All E2E Tests"
    
    local passed=0
    local failed=0
    local skipped=0
    
    # Get sorted list of playbooks
    local playbooks=$(ls -1 "$PLAYBOOKS_DIR"/*.yml 2>/dev/null | sort)
    
    for playbook in $playbooks; do
        if run_playbook "$playbook"; then
            ((passed++))
        else
            ((failed++))
        fi
    done
    
    # Summary
    print_header "Test Summary"
    echo -e "  ${GREEN}Passed:${NC}  $passed"
    echo -e "  ${RED}Failed:${NC}  $failed"
    echo -e "  ${YELLOW}Skipped:${NC} $skipped"
    echo ""
    
    if [[ $failed -gt 0 ]]; then
        print_error "Some tests failed!"
        exit 1
    else
        print_success "All tests passed!"
        exit 0
    fi
}

run_quick_test() {
    print_header "Quick Connectivity Test"
    run_playbook "${PLAYBOOKS_DIR}/00_connectivity.yml"
}

run_specific_playbook() {
    print_header "Running Specific Playbook: $SPECIFIC_PLAYBOOK"
    
    local playbook=$(ls -1 "${PLAYBOOKS_DIR}/${SPECIFIC_PLAYBOOK}"*.yml 2>/dev/null | head -1)
    
    if [[ -z "$playbook" ]]; then
        print_error "Playbook not found: ${SPECIFIC_PLAYBOOK}*.yml"
        exit 1
    fi
    
    run_playbook "$playbook"
}

compare_with_ansible() {
    print_header "Comparing Sansible vs Ansible"
    
    local san_result="${RESULTS_DIR}/${TIMESTAMP}_compare_neo.json"
    local ansible_result="${RESULTS_DIR}/${TIMESTAMP}_compare_ansible.json"
    local test_playbook="${PLAYBOOKS_DIR}/01_basic_modules.yml"
    
    print_info "Running with san..."
    san run -i "$INVENTORY" --json "$test_playbook" > "$san_result" 2>&1 || true
    
    print_info "Running with ansible-playbook..."
    ANSIBLE_STDOUT_CALLBACK=json ansible-playbook -i "$INVENTORY" "$test_playbook" > "$ansible_result" 2>&1 || true
    
    print_info "Comparing outputs..."
    echo "Sansible output: $san_result"
    echo "Ansible output: $ansible_result"
    
    # Basic comparison
    if [[ -f "$san_result" && -f "$ansible_result" ]]; then
        print_success "Both outputs generated - manual comparison recommended"
        print_info "Files saved in: $RESULTS_DIR"
    else
        print_warning "Could not generate comparison outputs"
    fi
}

# =============================================================================
# Parse Arguments
# =============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -q|--quick)
            QUICK_MODE=true
            shift
            ;;
        -p|--playbook)
            SPECIFIC_PLAYBOOK="$2"
            shift 2
            ;;
        -f|--forks)
            FORKS="$2"
            shift 2
            ;;
        -c|--compare)
            COMPARE_MODE=true
            shift
            ;;
        -j|--json)
            JSON_OUTPUT=true
            shift
            ;;
        --check)
            CHECK_MODE=true
            shift
            ;;
        --diff)
            DIFF_MODE=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# =============================================================================
# Main Execution
# =============================================================================

print_header "Sansible E2E Test Suite"
echo "Timestamp: $TIMESTAMP"
echo "Forks: $FORKS"

check_prerequisites

if $QUICK_MODE; then
    run_quick_test
elif $COMPARE_MODE; then
    compare_with_ansible
elif [[ -n "$SPECIFIC_PLAYBOOK" ]]; then
    run_specific_playbook
else
    run_all_tests
fi
