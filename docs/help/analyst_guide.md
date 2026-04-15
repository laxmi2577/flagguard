# 🔬 Analyst Dashboard — How To Use

Welcome to FlagGuard! As an **Analyst**, you can create projects, run scans, manage environments, configure webhooks, schedule scans, and generate reports.

---

## 1. ⚡ Analysis
The core tab — run feature flag analysis on your projects.
- **Create a Project:** Enter a project code + name → Click "+ Create"
- **Run a Scan:**
  1. Select a project from the dropdown
  2. Upload a **Flag Manifest** (.json or .yaml) — your feature flag configuration
  3. Optionally upload a **Source Archive** (.zip) — your codebase for AST analysis
  4. Check "AI Analysis" for LLM-powered explanations
  5. Click "⚡ Run Analysis"
- **Sub-tabs:** Charts (pie charts for status & severity), Dependency Graph (flag relationships), Report (markdown findings)

## 2. 🌍 Environments
Manage deployment environments for your projects.
- **Create:** Select a project → enter environment name (dev/staging/prod) → Click "Create"
- **Flag Overrides:** Provide JSON like `{"dark_mode": true, "beta": false}` to override flags per environment
- **Drift Detection:** Select two environments → "Compare Drift" to find flag mismatches between them

## 3. 📑 Reports
View and export historical analysis reports.
- **Generate:** Select a project → choose format (JSON/CSV/Markdown) → "Generate"
- **Executive Summary:** One-click summary with avg health, total scans, and latest status

## 4. 🏗️ IaC Scan
Scan Infrastructure-as-Code files for feature flag references.
- **Supported:** Terraform (.tf), YAML, JSON config files
- **How:** Upload your IaC file → Click "Analyze"
- **Output:** Detected flags with line numbers and matched patterns

## 5. 🔗 Webhooks
Set up notifications when scans complete.
- **Create:** Enter webhook URL + select project → "Create Webhook"
- **HMAC Signing:** All webhook payloads are cryptographically signed for security
- **Events:** Scan completed, conflicts detected, health score changed
- **Manage:** View, test, or delete existing webhooks

## 6. 📅 Scheduler
Automate recurring scans on a schedule.
- **Create:** Select a project → set cron schedule or interval → "Create Schedule"
- **Manage:** View active schedules, pause, resume, or delete them
- **Tip:** Use daily scans to catch flag drift early

## 7. 🔄 Lifecycle
Monitor flag health and age over time.
- **Stale flags (90+ days):** Yellow warning — consider reviewing or removing
- **Zombie flags:** Flags in config but never used in code — safe to remove
- **Age tracking:** See exactly how old each flag is

## 8. 🔀 Compare Scans
Compare two scans side-by-side to track changes.
- **How:** Select two scan IDs → "Compare"
- **What you see:** Added/removed/changed flags between scans
- **Tip:** Use this after major releases to catch unintended flag changes

## 9. 👤 Profile
Manage your account settings and data rights.
- **View profile:** Email, name, role, join date
- **Change password:** Enter current password → new password → confirm
- **Export data:** Download your personal data as JSON (GDPR Article 15)
- **Request deletion:** Submit a deletion request (reviewed by admin)

---

**Need user management or audit access?** Contact your admin to upgrade to **Admin** role.
