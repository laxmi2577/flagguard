# 👑 Admin Dashboard — How To Use

Welcome to FlagGuard! As an **Admin**, you have full system access — everything an Analyst can do, plus user management, audit logs, platform analytics, and system configuration.

---

## ⚡ Analysis
Run feature flag analysis — same as Analyst.
- **Create Project:** Enter code + name → "+ Create"
- **Run Scan:** Upload flag manifest + source archive → "⚡ Run Analysis"
- **Results:** Charts, dependency graph, report, lifecycle view

## 👥 User Approvals
Review and approve/reject new user sign-up requests.
- **How:** Click "Load Pending Requests"
- **Actions:**
  - **✅ Approve:** Creates a full user account with the requested role
  - **❌ Reject:** Denies access — user is notified on next login attempt
- **Tip:** Review the "Reason" field to understand why they need access

## 🧑‍💼 User Management
Full CRUD control over all user accounts.
- **View all users:** See email, role, status, creation date
- **Change role:** Upgrade viewer → analyst, or analyst → admin
- **Deactivate:** Temporarily disable a user's access without deleting
- **Delete:** Permanently remove a user account
- **Password Reset:** Force-reset a user's password

## 📋 Audit Log
Immutable record of all system actions.
- **What's logged:** Logins, scans, project creation, user changes, webhook deliveries
- **How:** Click "Load Audit Log" → Filter by date, user, or action type
- **Purpose:** SOC2 / ISO27001 compliance evidence
- **Tip:** Audit logs cannot be edited or deleted — they're append-only

## 📊 Platform Analytics
System-wide usage metrics and trends.
- **Metrics:** Total users, scans per day, avg health score, active projects
- **Charts:** Usage trends over time
- **Purpose:** Understand platform adoption and identify issues

## 🔌 Plugin Management
Configure and manage analysis plugins.
- **Built-in plugins:** Z3 SAT solver, tree-sitter AST parser, LLM remediation
- **How:** Enable/disable plugins, configure settings
- **Custom plugins:** Add your own analysis modules

## 🚦 CI/CD Gate
Configure automated pass/fail gates for CI/CD pipelines.
- **How:** Select a project → Set health score threshold
- **Integration:** Returns pass/fail for GitHub Actions, Jenkins, GitLab CI
- **Example:** Block deployments if health score drops below 70%

## 🌍 Environments
Manage deployment environments — same as Analyst.
- Create dev/staging/prod environments
- Track flag drift between environments

## 🔗 Webhooks
Configure webhook notifications — same as Analyst.

## 📑 Reports
View and export analysis reports — same as Analyst.

## 🏗 IaC Scans
Scan infrastructure files — same as Analyst.

## 🤖 AI Chat
AI-powered flag analysis assistant — same as Analyst.

## 🔔 Notifications
System alerts, user approval requests, and scan notifications.

## 👤 Profile & Settings
- **Account settings:** Change password, update email
- **Export data:** GDPR Article 15 data export
- **Deletion requests:** Review and process user deletion requests
- **System config:** Platform-wide settings

---

## 🔐 Admin-Only Security Notes
- All your actions are recorded in the Audit Log
- User management changes require re-authentication for sensitive operations
- Password resets generate temporary passwords that must be changed on first login
- Deletion requests follow a soft-delete workflow with 30-day recovery window
