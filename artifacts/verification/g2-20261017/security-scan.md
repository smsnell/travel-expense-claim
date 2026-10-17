# Agent Skill Security Scan Report

**Skill:** travel-expense-claim
**Directory:** /home/mike/travel-expense-claim/skills/travel-expense-claim
**Status:** [OK] SAFE
**Max Severity:** MEDIUM
**Scan Duration:** 0.52s
**Timestamp:** 2026-10-17T19:22:45.116979+00:00

## Summary

- **Total Findings:** 2
- **Critical:** 0
- **High:** 0
- **Medium:** 1
- **Low:** 0
- **Info:** 1

## Findings

### MEDIUM Severity

#### [MEDIUM] Outbound network request primitives that can transmit data externally

**Severity:** MEDIUM
**Category:** data_exfiltration
**Rule ID:** DATA_EXFIL_NETWORK_REQUESTS
**Location:** scripts/workflow.py:364

**Description:** Pattern detected: requests.get(

**Code Snippet:**
```
req=requests.get(rid)
```

**Remediation:** Ensure network operations are necessary and document allowed destinations

### INFO Severity

#### [INFO] Skill does not specify a license

**Severity:** INFO
**Category:** policy_violation
**Rule ID:** MANIFEST_MISSING_LICENSE
**Location:** SKILL.md

**Description:** Skill manifest does not include a 'license' field. Specifying a license helps users understand usage terms.

**Remediation:** Add 'license' field to SKILL.md frontmatter (e.g., MIT, Apache-2.0)

## Analyzers

The following analyzers were used:

- static_analyzer
- bytecode
- pipeline

