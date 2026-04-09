# FlagGuard Enterprise Terms of Service

**Effective Date:** April 5, 2026
**Version:** 3.0.0 (Enterprise Service Level Agreement)

---

## 1. Acceptance of Terms

By accessing, configuring, or actively utilizing the FlagGuard Enterprise Feature Flag Intelligence Platform—whether via the Gradio User Interface, the RESTful API endpoints, Webhook mechanisms, or direct CI/CD SDK pipelines—you ("Customer", "User", "You") formally agree to be bound by these exhaustive Terms of Service ("Agreement").

If you represent an organization or corporate entity, you warrant that you maintain the explicit legal authority to bind said entity to these constraints. *If you do not accept these terms, you must immediately terminate all interactions with the FlagGuard platform.*

## 2. Description of the Platform

### 2.1 The Service
FlagGuard operates as an advanced, logic-validating Feature Flag management suite. It incorporates:
*   Real-time toggling of software configurations.
*   Advanced logic verification using Z3 SAT-solver mathematics to detect flag collisions.
*   Role-Based Authorization protocols.
*   Webhook distributions.

### 2.2 System Volatility Warning
FlagGuard manipulates mission-critical infrastructure variables. While our SAT-solver dramatically reduces logical collision probability, **you** assume absolute risk when mapping Feature Flags to production execution pathways. We do not accept liability for software outages caused by mathematically valid but functionally destructive flag deployments.

## 3. Account Provisioning and Security

### 3.1 Authentication Supremacy
Access to the dashboard is conditionally granted via cryptographic JWT mechanisms. 
*   You must maintain the confidentiality of your provisioning credentials (Email/Password).
*   Any actions executed within the system logged against your internal `user_id` are explicitly deemed to be authorized by you.

### 3.2 Access Suspension (Admin Override)
System Administrators retain the unilateral right to freeze, demote, or terminate your `Analyst` or `Viewer` access if behavioral anomalies, severe API saturation, or internal policy breaches are detected.

## 4. Acceptable Use and Platform Integrity

### 4.1 Fair Usage and API Rate Limits
FlagGuard infrastructure is fortified via the `slowapi` enforcement engine. 
*   You agree not to bypass, spoof IPs, or execute distributed circumvention against our global rate limiters.
*   Aggressive scraping, synthetic load testing without explicit prior written authorization, or intentionally triggering SAT-solver timeouts via infinite recursive flag dependency inputs is strictly prohibited and classified as an Act of Sabotage.

*(Refer to our Acceptable Use Policy for an exhaustive matrix of prohibited actions).*

## 5. Intellectual Property Rights

### 5.1 Platform Ownership
All underlying logic, Gradio CSS arrays, Python middleware orchestration methodologies, pipeline definitions (Semgrep, Bandit integration chains), and SAT algorithms remain the exclusive intellectual property of FlagGuard Intelligence architecture. 

### 5.2 Customer Data Ownership
You retain absolute intellectual property rights over all distinct Feature Flag names, configuration keys, structural metadata, and business logic integrated *into* the platform. FlagGuard claims zero proprietary rights over your raw operational data.

## 6. Service Level Agreement (SLA) & Uptime

### 6.1 Enterprise Availability Guarantee
FlagGuard strives to maintain a 99.99% infrastructure uptime ratio, measured mathematically across rolling 90-day intervals, excluding mathematically mandated scheduled maintenance windows.

### 6.2 Exclusions
We are strictly not responsible for downtime resulting from:
*   AWS, GCP, or underlying structural IaaS total regional failures.
*   External DNS blackholing.
*   Client-side misconfiguration resulting in recursive internal API throttling.
*   Acts of God, cyber-warfare, or severe kinetic disruptions to communication grids.

## 7. Indemnification

You strictly agree to defend, indemnify, and hold mathematically and legally harmless FlagGuard, its subsidiaries, software engineers, and administrative staff against any and all claims, damages, multi-jurisdictional lawsuits, and financial losses arising fundamentally from:
1.  Your deployment of flags that destroy your own production environments.
2.  Your violation of the DPDPA, GDPR, or CCPA by feeding unauthorized PII into flag key-values.
3.  Gross negligence regarding credential management.

## 8. Limitation of Liability

IN NO EVENT SHALL FLAGGUARD OR ITS SUPPLIERS BE MATERIALLY RECOGNIZED AS LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES (INCLUDING LOSS OF PROFITS, DATA CORRUPTION, OR BUSINESS INTERRUPTION) ARISING OUT OF THE USE OR MATURE INABILITY TO USE THE FLAGGUARD SYSTEM. OUR AGGREGATE FINANCIAL LIABILITY FOR ANY DISPUTE IS STRICTLY CAPPED AT THE MONETARY VALUE OF YOUR ACTIVE SUBSCRIPTION TIER SPREAD OVER THE PRECEDING 30 DAYS.

## 9. Governing Law and Arbitration

### 9.1 Jurisdiction
This legal architecture shall be governed strictly by the laws of the Jurisdiction in which your Enterprise corporate charter is formally recognized, excluding specific conflicts of law provisions.

### 9.2 Dispute Resolution
Any major disputes unable to be resolved via internal engineering communication channels must be submitted to legally binding Arbitration prior to any formal class-action or civil litigation.

## 10. Entire Agreement

This Terms of Service document, when aggregated alongside the Privacy Policy and Acceptable Use Policy, constitutes the complete, monolithic understanding between Customer and Platform. It mathematically supersedes all previous verbal, written, or implied beta-testing negotiations.
