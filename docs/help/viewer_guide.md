# 👁 Viewer Dashboard — How To Use

Welcome to FlagGuard! As a **Viewer**, you have read-only access to monitor feature flag health across your projects.

---

## 📋 Scan History
View all past scans for your selected project.
- **How:** Select a project from the dropdown → Click "Load Scan History"
- **What you see:** Scan ID, status (passed/failed), health score, flag count, and date
- **Tip:** Use this to track how flag health changes over time

## 📊 Flag Charts
Visual charts showing your feature flag distribution.
- **Status Chart:** Shows how many flags are active, stale, or disabled
- **Severity Chart:** Shows critical vs. warning vs. info flag issues
- **How:** Select a project → charts auto-load

## 🕸 Dependency Graph
Interactive visualization of how your flags depend on each other.
- **How:** Select a project → click "Load Graph"
- **What to look for:** Circular dependencies (red lines) = potential conflicts
- **Tip:** Flags with many connections are high-risk — report them to your analyst

## 📄 Markdown Report
Download a full analysis report for your project.
- **How:** Select a project → Click "Generate Report"
- **Format:** Markdown with conflict details, health metrics, and recommendations

## 🔄 Flag Lifecycle
Track the age and staleness of your feature flags.
- **What it shows:** How old each flag is, when it was last modified, zombie flag warnings
- **Stale flags:** Flags not changed in 90+ days are marked as stale
- **Zombie flags:** Flags that exist in config but are never referenced in code

## 🤖 AI Chat
Ask questions about your feature flags using AI.
- **How:** Type a question like "What conflicts exist in my project?" → Press Enter
- **Examples:**
  - "Explain the conflict between flag_a and flag_b"
  - "Which flags are safe to remove?"
  - "What's the risk of enabling dark_mode?"
- **Tip:** The AI uses your actual scan data for grounded answers

## 🔔 Notifications
View system notifications and alerts.
- **What you see:** New scan results, flag health changes, admin announcements

## 👤 Profile & Data Rights
Manage your account and exercise your data rights.
- **Export My Data:** Download all your personal data as JSON (GDPR Article 15)
- **Request Account Deletion:** Submit a deletion request (reviewed by admin)

---

**Need more access?** Contact your admin to upgrade to **Analyst** role for creating projects and running scans.
