# 🔬 Analyst Dashboard — How To Use

Welcome to FlagGuard! As an **Analyst**, you can create projects, run scans, manage environments, configure webhooks, and generate reports.

---

## ⚡ Analysis
The core tab — run feature flag analysis on your projects.
- **Create a Project:** Enter a project code + name → Click "+ Create"
- **Run a Scan:**
  1. Select a project from the dropdown
  2. Upload a **Flag Manifest** (.json or .yaml) — your feature flag configuration
  3. Optionally upload a **Source Archive** (.zip) — your codebase for AST analysis
  4. Check "AI Analysis" for LLM-powered explanations
  5. Click "⚡ Run Analysis"
- **Results:** View conflict charts, dependency graph, and detailed findings
- **Sub-tabs:** Charts, Graph, Report, Lifecycle

## 📊 Charts
Visual breakdown of your scan results.
- **Flag Status:** Active vs. stale vs. disabled flags (pie chart)
- **Severity Distribution:** Critical / High / Medium / Low issues
- **Tip:** Click "Run Analysis" first to populate charts

## 🕸 Dependency Graph
Interactive visualization of flag relationships.
- **Nodes:** Each feature flag
- **Edges:** Dependencies between flags
- **Red connections:** Conflicts detected by the SAT solver
- **How:** Run an analysis → Graph auto-populates

## 📄 Report
Generate downloadable Markdown reports.
- **What's included:** Full conflict list, health score, remediation suggestions, flag inventory
- **How:** Run analysis → Click "Generate Report"

## 🔄 Flag Lifecycle
Monitor flag health over time.
- **Stale flags (90+ days):** Yellow warning — consider reviewing
- **Zombie flags:** Flags in config but never used in code — safe to remove
- **Age tracking:** See exactly how old each flag is

## 🌍 Environments
Manage deployment environments for your projects.
- **Create:** Name + select project → Click "Create Environment"
- **What it does:** Lets you track flag configurations across dev/staging/prod
- **Drift Detection:** Compare flags between environments to find mismatches

## 🔗 Webhooks
Set up notifications when scans complete.
- **Create:** Enter URL + select project → Click "Create Webhook"
- **HMAC Signing:** All webhook payloads are signed for security
- **Events:** Scan completed, conflicts detected, health score changed

## 📑 Reports
View and export historical analysis reports.
- **List:** All past reports with date, project, and health score
- **Download:** Click any report to download as Markdown

## 🏗 IaC Scans
Scan Infrastructure-as-Code files for flag misconfigurations.
- **Supported:** Terraform, CloudFormation, Kubernetes manifests
- **How:** Upload your IaC file → Click "Scan"

## 🤖 AI Chat
Ask the AI about your flags — powered by GraphRAG + fine-tuned LLM.
- **Examples:**
  - "What's wrong with my payment_v2 flag?"
  - "Generate a fix for the checkout conflict"
  - "Which flags can I safely deprecate?"

## 🔔 Notifications
System alerts and scan result notifications.

## 👤 Profile
Manage your account settings, export data, or request deletion.

---

**Need user management or audit access?** Contact your admin to upgrade to **Admin** role.
