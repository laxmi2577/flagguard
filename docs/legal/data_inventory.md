# FlagGuard Data Inventory & Classification

**Effective Date:** April 8, 2026
**Version:** 1.0.0
**Standard:** SOC2 CC6.1, ISO 27001 A.8, GDPR Record of Processing Activities (ROPA)

---

## 1. Purpose

This document maps every data element stored, processed, or transmitted by the FlagGuard platform. It defines the Classification Tier, lawful basis for processing, retention period, and encryption status for each data category. This document serves as FlagGuard's Record of Processing Activities (ROPA) as required under GDPR Article 30.

## 2. Data Controller Information

*   **Controller:** Laxmiranjan Sahu (Individual Developer / Open-Source Maintainer)
*   **Contact:** laxmiranjan444@gmail.com
*   **Jurisdiction:** India (DPDP Act 2023), with global applicability

## 3. Data Classification Tiers

| Tier | Label | Handling |
|------|-------|----------|
| T1 | **Public** | May be shared openly. No restrictions. |
| T2 | **Internal** | Accessible to authenticated users only. Standard protections. |
| T3 | **Confidential** | Restricted access. Encrypted at rest recommended. |
| T4 | **Sensitive (PII/HSD)** | Strict access controls. Encryption mandatory. Minimal retention. |

## 4. Complete Data Inventory

### 4.1 User Identity Data (T4 — Sensitive)

| Table | Column | Data Type | Purpose | Lawful Basis | Retention | Encryption |
|-------|--------|-----------|---------|-------------|-----------|------------|
| `users` | `email` | String | Account authentication | Contract | Until deletion | At rest (bcrypt hash for password) |
| `users` | `full_name` | String | Display name | Contract | Until deletion | Plaintext |
| `users` | `hashed_password` | String | Authentication | Contract | Until deletion | bcrypt hashed |
| `users` | `role` | String | RBAC authorization | Legitimate interest | Until deletion | Plaintext |
| `pending_users` | `email`, `full_name` | String | Signup approval workflow | Consent | 90 days after rejection | Plaintext |

### 4.2 Project & Analysis Data (T2 — Internal)

| Table | Column | Data Type | Purpose | Lawful Basis | Retention | Encryption |
|-------|--------|-----------|---------|-------------|-----------|------------|
| `projects` | `name`, `project_code` | String | Organize codebases | Contract | Until project deletion | Plaintext |
| `scans` | `result_summary` | JSON | Analysis results | Contract | 365 days | Plaintext |
| `scan_results` | `raw_json` | JSON | Detailed scan output | Contract | 365 days | Plaintext |
| `environments` | `flag_overrides` | JSON | Environment configs | Contract | Until deletion | Plaintext |

### 4.3 Security & Audit Data (T3 — Confidential)

| Table | Column | Data Type | Purpose | Lawful Basis | Retention | Encryption |
|-------|--------|-----------|---------|-------------|-----------|------------|
| `audit_logs` | `action`, `resource_type`, `ip_address` | String | Compliance audit trail | Legitimate interest | 365 days | Plaintext |
| `webhook_configs` | `url`, `secret` | String | Notification delivery | Contract | Until deletion | HMAC secret stored |
| `consent_logs` | `user_ip`, `user_agent`, `consent_type` | String | GDPR consent proof | Legal obligation | 3 years | Plaintext |

### 4.4 AI/ML Pipeline Data (T2 — Internal)

| Table | Column | Data Type | Purpose | Lawful Basis | Retention | Encryption |
|-------|--------|-----------|---------|-------------|-----------|------------|
| `llm_feedback` | `prompt`, `response`, `feedback` | Text | DPO training alignment | Consent | Until export | Plaintext |

### 4.5 Operational Data (T1 — Public)

| Table | Column | Data Type | Purpose | Lawful Basis | Retention | Encryption |
|-------|--------|-----------|---------|-------------|-----------|------------|
| `plugins` | `name`, `type`, `config` | String/JSON | Plugin registry | Contract | Permanent | Plaintext |
| `schedules` | `interval_minutes`, `is_active` | Integer/Bool | Scan scheduling | Contract | Until deletion | Plaintext |
| `notifications` | `title`, `message` | String | User alerts | Contract | 90 days | Plaintext |

## 5. Data Processing Activities

| Activity | Data Used | Purpose | Legal Basis | Recipients |
|----------|-----------|---------|------------|------------|
| User Login | Email, password hash | Authentication | Contract | Internal only |
| Cookie Consent | IP, user-agent | GDPR compliance proof | Legal obligation | Internal only |
| Code Scanning | Source code AST, flag configs | Feature flag analysis | Contract | Internal only |
| AI Remediation | Code snippets, conflict data | Generate fix patches | Consent (user-initiated) | Local LLM only (Ollama) |
| Risk Prediction | Git commit metadata | Predict conflict risk | Legitimate interest | Internal only |
| Audit Logging | User ID, action, IP | Security monitoring | Legitimate interest | Admin role only |

## 6. Cross-Border Data Flows

| Flow | Source | Destination | Safeguard |
|------|--------|-------------|-----------|
| Self-hosted deployment | User infrastructure | User infrastructure | No transfer |
| HuggingFace deployment | Global | US (HuggingFace Spaces) | Privacy Shield / SCCs |
| LLM inference | Local | Local (Ollama) | No external transfer |

## 7. Data Deletion Schedule

| Data Category | Auto-Purge Trigger | Method |
|---------------|-------------------|--------|
| Rejected signup requests | 90 days after rejection | SQL DELETE |
| Audit logs | 365 days from creation | SQL DELETE |
| Consent logs | 3 years from creation | SQL DELETE |
| Notifications | 90 days from creation | SQL DELETE |
| Deleted user accounts | 72 hours after admin approval | Anonymize + DELETE PII |

*Last Updated: April 2026*
