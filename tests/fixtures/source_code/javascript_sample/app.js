/**
 * Example JavaScript application with feature flag usage patterns.
 * Used for testing FlagGuard AST extraction.
 */

// Mock feature flags SDK
const flags = {
  isEnabled: (flagName) => false,
  isFeatureEnabled: (flagName) => false,
  variation: (flagName, defaultValue) => defaultValue,
  get: (flagName) => null,
};

// Mock LaunchDarkly client
const ldClient = {
  variation: (flagName, context, defaultValue) => defaultValue,
  boolVariation: (flagName, context, defaultValue) => defaultValue,
};

// ============================================
// Pattern 1: Method call on flags object
// ============================================
function processOrder(order) {
  if (flags.isEnabled("premium_checkout")) {
    return premiumCheckout(order);
  }
  return standardCheckout(order);
}

// ============================================
// Pattern 2: SDK-specific call (LaunchDarkly)
// ============================================
function getPaymentMethod(user) {
  if (ldClient.variation("new_payment_flow", user, false)) {
    return "stripe_v2";
  }
  return "stripe_v1";
}

// ============================================
// Pattern 3: Negated check
// ============================================
function shouldShowLegacyUI(request) {
  if (!flags.isEnabled("new_ui")) {
    return true;
  }
  return false;
}

// ============================================
// Pattern 4: Arrow function with flag
// ============================================
const getTheme = () => {
  return flags.isEnabled("dark_mode_enabled") ? "dark" : "light";
};

// ============================================
// Pattern 5: Class method with flag check
// ============================================
class PaymentProcessor {
  process(payment) {
    if (flags.isFeatureEnabled("premium_subscription_tier")) {
      return this.premiumProcess(payment);
    }
    return this.standardProcess(payment);
  }

  premiumProcess(payment) {
    return "premium";
  }

  standardProcess(payment) {
    return "standard";
  }
}

// ============================================
// Pattern 6: Nested flag checks (potential conflicts)
// ============================================
function checkoutFlow() {
  if (flags.isEnabled("new_checkout_flow")) {
    if (flags.isEnabled("payment_gateway_enabled")) {
      return "new_checkout_complete";
    } else {
      // Dead code if payment_gateway_enabled is always OFF
      throw new Error("Payment gateway required");
    }
  }
  return "legacy_checkout";
}

// ============================================
// Pattern 7: Multiple flags in conditions
// ============================================
function renderDashboard() {
  const isLoginV2 = flags.isEnabled("feature_login_v2");
  const isDashboardV2 = flags.isEnabled("feature_dashboard_v2");

  if (isLoginV2 && isDashboardV2) {
    return "full_v2_experience";
  } else if (isLoginV2) {
    return "partial_v2_experience";
  }
  return "legacy_experience";
}

// ============================================
// Pattern 8: Optional chaining (modern JS)
// ============================================
function safeFeatureCheck(flagName) {
  return flags?.isEnabled?.(flagName) ?? false;
}

// ============================================
// Pattern 9: Object bracket access pattern
// ============================================
const featureFlags = {
  premium_checkout: true,
  new_ui: false,
};

function checkFeatureObject(flagName) {
  if (featureFlags[flagName]) {
    return true;
  }
  return false;
}

// ============================================
// Pattern 10: Async function with flags
// ============================================
async function fetchDataWithFlag(userId) {
  if (flags.isEnabled("use_new_api")) {
    return await fetch(`/api/v2/users/${userId}`);
  }
  return await fetch(`/api/v1/users/${userId}`);
}

// Export for testing
module.exports = {
  processOrder,
  getPaymentMethod,
  getTheme,
  PaymentProcessor,
  checkoutFlow,
  renderDashboard,
};
