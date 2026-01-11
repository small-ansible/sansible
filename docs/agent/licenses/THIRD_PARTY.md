# Third-Party Licenses

This document tracks all vendored and ported third-party code in sansible.

## License Requirements

When adding third-party code:
1. Code must be under a permissive license (MIT, BSD, Apache 2.0)
2. License text must be included in this directory
3. Attribution must be added to this file
4. Any modifications must be documented

## Vendored/Ported Code

### Currently Included

*No third-party code has been vendored yet.*

### Template for Additions

```markdown
## [Package Name]

- **Source:** [URL]
- **Version/Commit:** [version or commit hash]
- **License:** [License type]
- **License File:** [filename in this directory]
- **What We Use:** [description]
- **Modifications:** [list of changes or "None"]
```

---

## Future Candidates

These may be vendored/ported in future milestones:

### For WinRM/NTLM (M4)
- **ntlm-auth**: Pure Python NTLM implementation
  - License: MIT
  - Status: Under evaluation

### For Pure Python SSH (Phase B, optional)
- **asyncssh** (reference only, not vendored)
  - License: EPL-2.0 (not compatible for vendoring)
  - Status: Reference implementation only

---

## License Compatibility

| License | Compatible | Notes |
|---------|------------|-------|
| MIT | ✓ | Preferred |
| BSD-2-Clause | ✓ | Good |
| BSD-3-Clause | ✓ | Good |
| Apache-2.0 | ✓ | Good, note patent clause |
| ISC | ✓ | Good |
| MPL-2.0 | ⚠️ | File-level copyleft, isolate |
| LGPL-2.1+ | ⚠️ | Dynamic linking only |
| GPL-2.0+ | ✗ | Not compatible |
| AGPL-3.0 | ✗ | Not compatible |

---

## Audit Log

| Date | Action | Package | License |
|------|--------|---------|---------|
| 2026-01-10 | Initial setup | - | - |
