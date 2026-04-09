# FlagGuard Acceptable Use Policy (AUP)

**Effective Date:** April 5, 2026
**Version:** 1.0.0 (Enterprise Enforcement)

---

## 1. Objective of this Policy

This Acceptable Use Policy ("AUP") defines the rigorous boundaries of compliant interaction with the FlagGuard Enterprise Intelligence Platform. This document is not a suggestion; it represents mandatory technical operational parameters. 

FlagGuard exists to manage high-velocity Feature Flag states, execute intricate logic-collision mathematics, and enforce strict Role-Based Access Controls (RBAC). Any usage of this software that falls outside of these primary vectors threatens platform stability and is deemed a hostile policy violation.

## 2. Who Does This Apply To?

This policy maps directly to every single distinct entity possessing an authentication token against our API:
1.  **System Administrators:** (Root level override capabilities).
2.  **Analysts:** (Write-access flag togglers).
3.  **Viewers:** (Read-only auditors).
4.  **Service Accounts:** (CI/CD automated tokens, SDK wrappers).

## 3. Strictly Prohibited Activities

You are explicitly forbidden from executing, attempting to execute, or orchestrating the following hostile vectors:

### 3.1 Network and Application Abuse
*   **Volumetric Assault:** Firing concurrent API requests at a methodology or volume that intentionally triggers or attempts to bypass our `slowapi` rate-limiting firewalls.
*   **Fuzzing and Reverse Engineering:** Utilizing tools such as BurpSuite, OWASP ZAP, or automated scanners against production endpoints without explicit engineering authorization and an active Bug Bounty waiver.
*   **Algorithmic Sabotage (SAT-Solver Exploitation):** Intentionally constructing recursively infinite or infinitely dense Feature Flag dependency graphs designed specifically to cause CPU deadlock inside our Z3 mathematical resolution engine.
*   **Cross-Site Malfeasance:** Attempting XSS, SQLi, or DOM-based exploitation payloads inside Flag names, project descriptions, or webhook payload arrays.

### 3.2 Data Toxicity and Governance Breaches
FlagGuard is an infrastructure orchestrator, **not a secure vault for raw PII**.
*   You must **never** inject raw user passwords, Credit Card PANs, cryptographic private keys, or HIPAA/ePHI diagnostic readouts directly into a Feature Flag Key, Value, or Description string.
*   You agree that flag keys operate as metadata pointers, not high-entropy encrypted data silos.

### 3.3 Authorization and RBAC Circumvention
*   **Token Sniffing:** Attempting to extract, reverse engineer, or hijack another user's `fg_session` JWT token.
*   **Privilege Escalation:** Employing API manipulation to execute `DELETE /project` commands while authenticated under a standard Viewer or Analyst role.
*   **Account Sharing:** Distributing Analyst credentials among multiple personnel. Flag audit trails mandate immutable 1:1 user-to-action mapping.

### 3.4 Operational Integrity
*   Utilizing the FlagGuard webhook broadcasting system to construct spam botnets or C2 (Command and Control) proxy communication.
*   Overwhelming the SQLite/PostgreSQL Database engines by running aggressive concurrent `CREATE` and `DELETE` requests in infinite while-loops during automated tests against the production cluster.

## 4. Zero-Tolerance Environment

FlagGuard is designed for Enterprise SOC2 frameworks. We do not issue warnings for malicious operational interference.

### 4.1 Monitoring and Enforcement
Our `AuditMiddleware` persistently logs all state modifications. Heuristic triggers connected to these logs actively search for signatures matching the prohibited activities outlined in Section 3.

### 4.2 Repercussions of Violation
If an active `fg_session` or static API token is mathematically correlated with AUP violations, FlagGuard infrastructure maintains the right to immediately execute the following countermeasures without prior notification:
1.  **Token Annihilation:** Immediate nullification of the user's JWT status.
2.  **IP Blackholing:** Routing the offending host IP to `/dev/null` at the load balancer firewall level.
3.  **Auditorial Escalation:** Dispatching the forensic log array directly to your organization's Chief Information Security Officer (CISO) or equivalent Administrator.
4.  **Civil Liability:** If your algorithmic sabotage triggers a cascading failure that disrupts the SLA metrics of other tenants on a shared FlagGuard cluster, we WILL pursue total financial remediation.

## 5. Security Research & Disclosure

### 5.1 Good Faith Hacking
If you are an internal red-team operator or a security analyst and you discover a genuine architectural vulnerability (e.g., you successfully breached the SAT-solver sandbox or compromised the HMAC webhook signer), you must immediately cease testing and transition to the reporting phase.

### 5.2 Responsible Disclosure
Do not dump FlagGuard zero-days onto Twitter or HackerNews. Submit detailed forensic logs and Proof of Concept (PoC) scripts securely to the designated FlagGuard security contact. 

## 6. Policy Amendments

FlagGuard guarantees that this AUP will evolve aggressively as new cyber-kinetic paradigms shift. When this AUP is modified, an architectural lock will force all users to digitally re-sign/re-accept this document inside the Gradio UI modal before their API keys regain active transmission capabilities.

*Final Adherence Clause.*
