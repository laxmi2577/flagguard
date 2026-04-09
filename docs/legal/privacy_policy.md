# FlagGuard Enterprise Privacy Policy

**Effective Date:** April 5, 2026
**Version:** 2.2.0 (Enterprise Compliant)

---

## 1. Introduction and Scope

FlagGuard Enterprise Intelligence ("FlagGuard", "we", "us", or "our") is deeply committed to protecting the privacy, security, and integrity of the data processed within our ecosystem. This Privacy Policy strictly governs the collection, processing, and retention of personal and telemetry data across all Enterprise cloud modules, on-premise deployments, and SaaS environments.

This policy is meticulously designed to comply with rigorous global frameworks, including:
*   **General Data Protection Regulation (GDPR) (EU & UK)**
*   **California Consumer Privacy Act (CCPA) and CPRA**
*   **Digital Personal Data Protection Act (DPDPA 2023) (India)**
*   **Service Organization Control 2 (SOC2 Type II) Trust Principles**
*   **ISO/IEC 27001:2022 Security Standards**

By utilizing FlagGuard's Feature Flag Analytics API, Gradio UI Dashboard, or CLI interfaces, you acknowledge and agree to the data handling practices outlined herein.

## 2. Data Classification Matrix

To ensure rigorous handling, all ingested data is mapped against our proprietary Data Classification Matrix.

### 2.1 Public Data
*   General marketing metadata.
*   Open-source platform commits.
*   Public API schema definitions.

### 2.2 Internal Telemetry (Confidential)
*   **IP Addresses:** Captured purely for rate-limiting, DDoS mitigation (via `slowapi`), and threat heuristics.
*   **Session Tokens:** Ephemeral JWT constructs used exclusively for verifying RBAC roles (Admin/Analyst/Viewer).
*   **Browser Fingerprints:** Basic user-agent mappings to ensure Gradio frontend rendering compatibility and websocket stability.

### 2.3 Highly Sensitive Data (HSD)
*   User Passwords (Never stored plaintext; utilizes bcrypt cryptographic iteration).
*   Production Environment Secrets (API Keys, Webhook HMAC signatures).
*   Feature Flag topological logic that may inadvertently expose upcoming mergers, acquisitions, or stealth product launches.

*Note: FlagGuard employs zero-knowledge architecture regarding the business context of your flags.*

## 3. How We Collect Your Data

### 3.1 Automated Infrastructure Harvesting
When you interact with the FlagGuard dashboard, our `AuditMiddleware` intercepts the HTTP transmission layer. We automatically record the `Method`, `URL Path`, `Status Code`, and execution duration to enforce immutable audit trails.

### 3.2 Account Provisioning
During the "Request Access" workflow, we collect your Full Name, Email Address, and the Business Justification for requiring plateau access. 

### 3.3 CI/CD and SDK Ingestion
When your internal servers connect to our REST API via our Python or Node.js SDKs, we collect execution metadata, deployment timestamps, and error traces utilizing our backend Prometheus/Grafana pipeline.

...

## 4. How We Process and Utilize Data

Our processing pipelines are strictly bound by the principle of **Data Minimization**.

### 4.1 Security Optimization
All collected IP addresses and backend interaction signatures are streamed into our threat intelligence engine. This prevents automated bot scraping, unauthorized webhook tampering, and saturation attacks.

### 4.2 Application Stabilization
We utilize anonymous error tracking to identify SAT-solver timeouts, database deadlock states, and Gradio WebSocket disruptions. This telemetry does not contain flag payloads.

### 4.3 Mandatory Audit Compliance
We maintain immutable stdout logs of all `POST`, `PUT`, and `DELETE` requests. This ensures our Enterprise clients can pass their internal compliance audits and track exactly which Analyst toggled a high-risk production flag.

## 5. Cookie Consent and Session Architecture

FlagGuard employs a strict, explicit-consent cookie protocol.

*   **Session Cookies (`fg_session`):** Essential cookies carrying encrypted JWT payloads required to keep you logged in. These cannot be disabled.
*   **Consent Marker (`flagguard_consent`):** A boolean register indicating whether you clicked "Accept All" or "Reject" on our global tracking modal.
*   **Analytics Cookies:** If explicitly accepted, these track your UI navigation paths through the Viewer/Analyst dashboards to help us optimize UI/UX. If rejected, our `CookieConsentMiddleware` preemptively blocks all traffic to `/api/v1/analytics` at the FastApi router level, guaranteeing zero metric collection.

## 6. Access Controls and Security

### 6.1 Role-Based Access Control (RBAC)
We employ strict RBAC segregation. 'Viewers' cannot access 'Analyst' routes. 'Analysts' cannot access 'Admin' provisioning. Your data is isolated and projected exclusively based on deterministic cryptographic authorization headers.

### 6.2 Encryption Standards
*   **In Transit:** All APIs, Webhooks, and UI traffic require TLS 1.3 encryption.
*   **At Rest:** The SQLite / PostgreSQL primary database utilizes transparent farm encryption.

## 7. Data Retention and Deletion

Data is not kept indefinitely.

1.  **Orphaned Flags:** Automatically pruned based on the `LifecycleManager` engine threshold.
2.  **Audit Logs:** Held in cold storage for exactly 365 days to satisfy standard auditor requirements, then permanently purged.
3.  **Account Termination:** If an Admin deletes your account, all personal metadata (email, name) is wiped from the `users` table within 72 hours. Your historical flag actions remain in the immutable audit log for statistical integrity but are anonymized.

## 8. International Data Transfers

If your data is transferred outside the European Economic Area (EEA), we ensure adequate legal protections are enforced via Standard Contractual Clauses (SCCs). Data localization protocols enforce that EU telemetry is processed entirely within `eu-central-1` architecture where configured.

## 9. Your Rights

Depending on your jurisdiction (GDPR, CCPA), you reserve the absolute right to:
1.  **Request Access** to the structured JSON telemetry we hold on your user profile.
2.  **Request Deletion** of all non-audit binding data (Right to be Forgotten).
3.  **Opt-Out** of advanced heuristics dynamically by adjusting your Cookie preferences in the interface.

To exercise these rights, initiate a formal Webhook request or contact your System Administrator.

## 10. Modifications to this Policy

FlagGuard reserves the right to modify this legal framework to adapt to evolving technological threats and regulatory jurisprudence. All major revisions will trigger an automated `banner update` forcing users to re-validate their consent upon next login.

*End of Policy.*
