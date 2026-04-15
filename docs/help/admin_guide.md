# 👑 Admin Dashboard — How To Use

Welcome to FlagGuard! As an **Admin**, you have full system access — everything an Analyst can do, plus user management, audit logs, platform analytics, and system configuration.

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
- **Flag Overrides:** Provide JSON to override specific flags per environment
- **Drift Detection:** Select two environments → "Compare Drift" to find flag mismatches

## 3. 📑 Reports
View and export historical analysis reports.
- **Generate:** Select a project → choose format (JSON/CSV/Markdown) → "Generate"
- **Executive Summary:** One-click summary with avg health, total scans, and latest status

## 4. 🏗️ IaC Scan
Scan Infrastructure-as-Code files for feature flag references.
- **Supported:** Terraform (.tf), YAML, JSON config files
- **How:** Upload your IaC file → Click "Analyze"
- **Output:** Detected flags with line numbers and matched patterns

## 5. 🚦 CI/CD Gate
Configure automated pass/fail gates for CI/CD pipelines.
- **How:** Select a project → Set minimum health % threshold → "Run Gate Check"
- **Result:** ✅ PASS or ❌ FAIL with full gate report
- **Integration:** Use the health score in GitHub Actions, Jenkins, or GitLab CI to block bad deployments

## 6. 📋 Audit Log
Immutable record of all system actions.
- **Filter:** By action type (create, update, delete, scan, login) and resource type (project, user, webhook)
- **Metrics:** Total events count and today's activity
- **Stats:** Top actions and top users breakdown
- **Export:** Download audit trail as JSON or CSV for compliance (SOC2/ISO27001)
- **Note:** Audit logs are append-only — they cannot be edited or deleted

## 7. 📊 Analytics
Platform-wide usage metrics and trends.
- **Overview:** Total users, projects, scans, and average health score
- **Leaderboard:** Top users ranked by scan activity
- **Project Health Cards:** Health score and last scan date for every project

## 8. 🔌 Plugins
Configure and manage analysis plugins.
- **View:** Click "Load Plugins" to see all registered plugins
- **Register:** Enter name, type (parser/rule), version, and description
- **Toggle:** Enable/disable plugins by ID
- **Remove:** Permanently delete a plugin registration

## 9. ✅ User Approvals
Review and approve/reject new user sign-up requests.
- **How:** Click "Refresh Requests" to load pending signups
- **Approve:** Creates a full user account with the requested role — user gets notified
- **Reject:** Denies access with an optional reason
- **Tip:** Review the "Reason" field to understand why they need access

## 10. 👥 User Management
Full control over all user accounts.
- **View all users:** See ID, email, role, active status, join date
- **Change role:** Upgrade/downgrade between viewer, analyst, and admin
- **Reset password:** Force-reset any user's password (min 6 characters)
- **Deactivate:** Temporarily disable a user's access (cannot deactivate yourself)
- **Project Access (RBAC):** Assign users to specific projects with read or write access

## 11. 👤 Profile
Manage your own account settings.
- **View profile:** Email, name, role, join date
- **Change password:** Enter current password → new password → confirm

## 🔐 Data Rights & DSAR (below tabs)
Located below the main tabs — GDPR/CCPA/DPDP compliance tools.
- **Export My Data:** Download all your personal data as JSON
- **Request Deletion:** Submit a deletion request (soft-delete with admin review)
- **Admin Review:** Approve or reject pending deletion requests from other users

---

**Security Note:** All your actions are recorded in the Audit Log. Audit logs are append-only and cannot be modified.
