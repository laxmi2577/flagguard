# 👁 Viewer Dashboard — How To Use

Welcome to FlagGuard! As a **Viewer**, you have read-only access to monitor feature flag health across your assigned projects.

---

## 1. 📋 Scan History
View all past scans for your selected project.
- **How:** Select a project from the dropdown → Click "Load Scan History"
- **What you see:** Scan ID, status (passed/failed), health score, flag count, and date
- **Tip:** Use this to track how flag health changes over time

## 2. 📊 Analytics
Visual charts showing your feature flag distribution.
- **Status Chart:** Shows how many flags are active, stale, or disabled (pie chart)
- **Severity Chart:** Shows critical vs. warning vs. info flag issues
- **How:** Select a project → charts auto-load after a scan

## 3. 📄 Report
Download a full analysis report for your project.
- **How:** Select a project → Click "Generate Report"
- **Format:** Markdown with conflict details, health metrics, and recommendations

## 4. 🕸 Dependency Graph
Interactive visualization of how your flags depend on each other.
- **How:** Select a project → click "Load Graph"
- **What to look for:** Circular dependencies (red lines) = potential conflicts
- **Tip:** Flags with many connections are high-risk — report them to your analyst

## 5. 🔄 Flag Lifecycle
Track the age and staleness of your feature flags.
- **Stale flags (90+ days):** Yellow warning — consider reviewing or removing
- **Zombie flags:** Flags that exist in config but are never referenced in code — safe to remove
- **Age tracking:** See exactly how old each flag is

## 6. 🔍 Flag Search
Search for specific flags across your projects.
- **How:** Enter a flag name or keyword → results show matching flags with details
- **Tip:** Use this when you need to quickly find a specific flag's status

## 7. 🤖 AI Chat
Ask questions about your feature flags using AI.
- **How:** Type a question → Press Enter
- **Examples:**
  - "What conflicts exist in my project?"
  - "Explain the conflict between flag_a and flag_b"
  - "Which flags are safe to remove?"
- **Tip:** The AI uses your actual scan data for grounded, accurate answers

## 8. 👤 Profile
Manage your account settings and data rights.
- **View profile:** Email, name, role, join date
- **Change password:** Enter current password → new password → confirm
- **Export My Data:** Download all your personal data as JSON (GDPR Article 15)
- **Request Deletion:** Submit a deletion request (reviewed by admin)

---

**Need more access?** Contact your admin to upgrade to **Analyst** role for creating projects and running scans.
