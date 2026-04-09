# FlagGuard AI Transparency Statement

**Effective Date:** April 8, 2026
**Version:** 1.0.0
**Regulation Reference:** GDPR Article 22, EU AI Act, India DPDP Act 2023

---

## 1. Purpose

This document discloses how FlagGuard uses Artificial Intelligence (AI) and automated decision-making systems within its platform. We believe in full transparency regarding how AI processes your data and influences platform outputs.

## 2. AI Systems Used in FlagGuard

FlagGuard employs the following AI and automated decision-making components:

### 2.1 Z3 SAT Solver (Formal Verification)
*   **What it does:** Translates feature flag logic into Boolean satisfiability problems and mathematically proves whether code paths are impossible, conflicting, or dead.
*   **Type:** Deterministic mathematical solver — NOT a machine learning model.
*   **Human oversight:** Results are displayed for human review. No code is modified automatically.
*   **Data processed:** Feature flag configurations (JSON/YAML) and source code AST structures. No personal data is processed.

### 2.2 GraphRAG Coder Agent (LLM-Based)
*   **What it does:** Generates code patches to fix detected feature flag conflicts. Uses a Hybrid Retriever (ChromaDB semantic search + NetworkX call graph) to retrieve relevant source code context, then generates a `git diff` patch.
*   **Model:** Ollama / Gemma 2B (local inference — no data leaves your infrastructure).
*   **Human oversight:** ALL generated patches are displayed for manual human review. Patches are NEVER applied automatically. Users must explicitly copy and apply them.
*   **Verification:** Every generated patch is re-verified through the Z3 SAT solver before being shown to the user. Only mathematically proven-safe patches reach the user interface.

### 2.3 Z3 Verifier Agent
*   **What it does:** Mathematically verifies that AI-generated code patches do not introduce new feature flag conflicts.
*   **Type:** Deterministic formal verification — NOT a machine learning model.
*   **Data processed:** Proposed code patches (no personal data).

### 2.4 XGBoost Risk Predictor
*   **What it does:** Predicts the probability that a git commit will introduce feature flag conflicts, based on 14 engineered features from commit metadata (files modified, lines changed, commit hour, etc.).
*   **Type:** Classical machine learning model (gradient-boosted decision trees).
*   **Human oversight:** Risk scores are advisory only. No automated actions are taken based on risk predictions.
*   **Explainability:** Every risk prediction includes a SHAP (SHapley Additive exPlanations) waterfall chart showing exactly which features contributed to the score, ensuring full interpretability.

### 2.5 SHAP Explainer
*   **What it does:** Provides per-prediction feature attribution analysis for the XGBoost risk model using SHAP TreeExplainer.
*   **Purpose:** Ensures that risk predictions are interpretable and auditable, not black-box outputs.

## 3. What We Do NOT Do

*   We do **NOT** use AI to make access control decisions. RBAC (Role-Based Access Control) is entirely rule-based.
*   We do **NOT** use AI to process, profile, or score individual users.
*   We do **NOT** use AI for targeted advertising, behavioral tracking, or user segmentation.
*   We do **NOT** send your source code to external AI APIs (all LLM inference runs locally via Ollama).

## 4. Your Rights Regarding AI

Under GDPR Article 22 and the India DPDP Act 2023, you have the right to:

1.  **Be informed:** This document fulfills that obligation.
2.  **Request human review:** All AI outputs in FlagGuard are already subject to mandatory human review before any action is taken.
3.  **Object to automated decisions:** Since FlagGuard does not make automated decisions that produce legal or significant effects on individuals, this right is satisfied by design.
4.  **Request an explanation:** SHAP explainability is built into the risk prediction system. For other AI outputs, contact our Grievance Officer.

## 5. Bias and Fairness

*   The Z3 SAT solver operates on discrete mathematical logic — it cannot exhibit bias.
*   The XGBoost risk model is trained on commit metadata (code metrics, timestamps) — it does not process any demographic, personal, or protected-class data.
*   We do not use AI to evaluate human subjects, make hiring decisions, or perform credit scoring.

## 6. Contact

For questions about AI usage in FlagGuard:
*   **Grievance Officer:** Laxmiranjan Sahu
*   **Email:** [laxmiranjan444@gmail.com](mailto:laxmiranjan444@gmail.com)

*Last Updated: April 2026*
