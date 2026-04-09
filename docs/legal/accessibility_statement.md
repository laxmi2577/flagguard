# FlagGuard Accessibility Statement

**Effective Date:** April 8, 2026
**Version:** 1.0.0
**Standard:** WCAG 2.2 Level AA

---

## 1. Our Commitment

FlagGuard is committed to ensuring digital accessibility for all users, including those with disabilities. We continuously work to improve the accessibility and usability of the FlagGuard Enterprise Dashboard to ensure compliance with applicable accessibility standards and regulations, including:

*   **ADA (Americans with Disabilities Act)** — United States
*   **European Accessibility Act (EAA)** — European Union
*   **Equality Act 2010** — United Kingdom
*   **Rights of Persons with Disabilities (RPwD) Act, 2016** — India

## 2. Accessibility Features

FlagGuard implements the following accessibility measures:

### 2.1 Visual Accessibility
*   **Color Contrast:** All text elements maintain a minimum contrast ratio of 4.5:1 against their backgrounds (WCAG 2.2 AA), validated across both Dark and Light modes.
*   **Non-Color Indicators:** Status information (Success, Warning, Error) is communicated via icons and text labels in addition to color, ensuring colorblind users can interpret states.
*   **Readable Typography:** We use the Inter and Outfit font families at sizes no smaller than 0.75rem, with generous line-height (1.6) for body text.

### 2.2 Motor Accessibility
*   **Keyboard Navigation:** All interactive elements (buttons, dropdowns, tabs, forms) are reachable and operable via keyboard alone (Tab, Enter, Escape).
*   **Focus Indicators:** Visible focus outlines (2px solid gold) appear on all interactive elements when navigated via keyboard (`:focus-visible`).
*   **Skip Navigation:** A "Skip to main content" link is available for keyboard users.

### 2.3 Motion Sensitivity
*   **Reduced Motion:** FlagGuard respects the `prefers-reduced-motion` operating system setting. When enabled, all CSS animations, transitions, and scroll behaviors are disabled.

### 2.4 Semantic Structure
*   **ARIA Labels:** All interactive elements include `aria-label` attributes for screen reader compatibility.
*   **Semantic HTML:** We use proper HTML5 semantic elements (`<footer>`, `<nav>`, `<main>`, `role` attributes) throughout the interface.
*   **Heading Hierarchy:** Pages follow a logical heading structure (h1 → h2 → h3) for screen reader navigation.

## 3. Known Limitations

While we strive for full WCAG 2.2 AA compliance, the following limitations exist due to the Gradio framework:

*   **Dynamic Component Loading:** Gradio renders components asynchronously via Svelte, which may cause brief screen reader announcement delays.
*   **Complex Data Visualizations:** Mermaid.js dependency graphs and SHAP waterfall plots may not be fully accessible to screen readers. We provide equivalent text-based data tables where possible.
*   **Third-Party Form Controls:** Some Gradio-native dropdowns and radio buttons inherit framework-level ARIA attributes that we cannot fully customize.

## 4. Feedback & Contact

If you experience accessibility barriers while using FlagGuard, please contact us:

*   **Email:** [laxmiranjan444@gmail.com](mailto:laxmiranjan444@gmail.com)
*   **GitHub Issues:** [github.com/laxmi2577/flagguard/issues](https://github.com/laxmi2577/flagguard/issues)

We aim to respond to accessibility feedback within 5 business days and provide a resolution or workaround within 30 days.

## 5. Ongoing Efforts

*   Quarterly accessibility reviews using Lighthouse and axe-core
*   Ongoing screen reader testing (NVDA, VoiceOver)
*   Keyboard-only navigation verification per major release
*   Community-driven accessibility issue tracking via GitHub

*Last Reviewed: April 2026*
