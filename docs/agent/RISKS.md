# Risk Register

This document tracks risks that could derail the sansible project.

## Risk Matrix

| Risk | Likelihood | Impact | Mitigation Status |
|------|------------|--------|-------------------|
| R1: PyYAML C ext sneaks in | Medium | High | Mitigated |
| R2: WinRM auth complexity | High | High | Planned |
| R3: SSH edge cases | Medium | Medium | Planned |
| R4: Performance issues | Medium | Medium | Accepted |
| R5: Upstream drift | Medium | Low | Accepted |
| R6: Windows path edge cases | Medium | Medium | In Progress |

---

## R1: PyYAML C Extension

**Description:** PyYAML can use libyaml C extension which would break pure-Python requirement.

**Likelihood:** Medium  
**Impact:** High (breaks core constraint)

**Indicators:**
- `dep_audit.py` finds `.so` or `.pyd` files
- Import of `CLoader` or `CDumper`

**Mitigation:**
1. Always use `yaml.SafeLoader` not `yaml.CSafeLoader`
2. `dep_audit.py` runs in CI to catch this
3. Document in DECISIONS.md

**Status:** Mitigated ✓

---

## R2: WinRM Authentication Complexity

**Description:** NTLM and especially Kerberos authentication are complex to implement in pure Python.

**Likelihood:** High  
**Impact:** High (WinRM transport may not work in all environments)

**Indicators:**
- Authentication failures in enterprise environments
- Complaints about Kerberos not working

**Mitigation:**
1. Start with Basic auth (requires HTTPS)
2. Implement NTLM using pure Python port (permissive license)
3. For Kerberos: design plugin interface for future implementation
4. Document authentication limitations clearly
5. Allow credential pass-through strategies

**Status:** Planned

---

## R3: SSH Edge Cases

**Description:** Subprocess-based SSH may not handle all edge cases (prompts, timeouts, encoding).

**Likelihood:** Medium  
**Impact:** Medium (some hosts may not work)

**Indicators:**
- Hangs during SSH connection
- Password prompts not handled
- Encoding errors in output

**Mitigation:**
1. Use connection multiplexing (ControlMaster)
2. Set strict timeouts
3. Force SSH batch mode
4. Handle common prompts/errors
5. Clear error messages for debugging

**Status:** Planned

---

## R4: Performance Issues

**Description:** Pure Python may be slower than compiled alternatives.

**Likelihood:** Medium  
**Impact:** Medium (slow for large inventories)

**Indicators:**
- Noticeably slower than upstream Ansible
- High CPU usage during YAML parsing or execution

**Mitigation:**
1. Accept some performance penalty for portability
2. Profile and optimize hot paths
3. Ensure concurrency works correctly
4. Document performance expectations

**Status:** Accepted

---

## R5: Upstream Ansible Drift

**Description:** Upstream Ansible changes syntax/behavior we depend on.

**Likelihood:** Medium  
**Impact:** Low (we're implementing a compatible subset)

**Indicators:**
- New playbook features we don't support
- Syntax changes break our parser

**Mitigation:**
1. Target specific Ansible version compatibility
2. Document supported features
3. Track upstream releases for breaking changes
4. Focus on stable, widely-used features

**Status:** Accepted

---

## R6: Windows Path Edge Cases

**Description:** Windows paths have many edge cases (UNC, long paths, reserved names).

**Likelihood:** Medium  
**Impact:** Medium (operations fail on certain paths)

**Indicators:**
- Errors with network shares (\\\\server\\share)
- Failures with paths >260 characters
- Issues with names like CON, NUL, PRN

**Mitigation:**
1. Use pathlib where possible
2. Test with UNC paths
3. Enable long path support where available
4. Document path limitations

**Status:** In Progress

---

## Risk Response Strategies

| Strategy | When to Use |
|----------|-------------|
| **Avoid** | Eliminate risk by changing approach |
| **Mitigate** | Reduce likelihood or impact |
| **Transfer** | Shift risk elsewhere (rare in OSS) |
| **Accept** | Acknowledge and monitor |

## Adding New Risks

When adding a risk:
1. Assign a unique ID (R#)
2. Rate likelihood: Low/Medium/High
3. Rate impact: Low/Medium/High
4. Identify indicators
5. Plan mitigation
6. Set status

Update the risk matrix at the top of this document.
