"""Example Python application with feature flag usage patterns.

This file demonstrates various feature flag patterns that
FlagGuard can detect and analyze. Used for testing.
"""

from typing import Any


# Mock feature flag SDK
class FeatureFlags:
    """Mock feature flag client for demonstration."""
    
    @staticmethod
    def is_enabled(flag_name: str) -> bool:
        """Check if a flag is enabled."""
        return False
    
    @staticmethod
    def is_feature_enabled(flag_name: str) -> bool:
        """Check if a feature is enabled."""
        return False
    
    @staticmethod
    def variation(flag_name: str, default: Any) -> Any:
        """Get a flag variation value."""
        return default


# Global instance
feature_flags = FeatureFlags()


def is_enabled(flag_name: str) -> bool:
    """Global flag check function."""
    return feature_flags.is_enabled(flag_name)


# ============================================
# Pattern 1: Simple function call in if statement
# ============================================
def process_order(order: dict) -> str:
    """Process an order with premium checkout if enabled."""
    if is_enabled("premium_checkout"):
        # This code runs when premium_checkout is ON
        return "premium_checkout_processed"
    return "standard_checkout_processed"


# ============================================
# Pattern 2: Method call on SDK object
# ============================================
def get_payment_method(user: dict) -> str:
    """Get payment method based on feature flags."""
    if feature_flags.is_feature_enabled("new_payment_flow"):
        return "stripe_v2"
    return "stripe_v1"


# ============================================
# Pattern 3: Negated flag check
# ============================================
def show_legacy_ui(request: dict) -> bool:
    """Show legacy UI if new UI is disabled."""
    if not is_enabled("new_ui"):
        return True
    return False


# ============================================
# Pattern 4: Flag with dependency (conflict scenario)
# ============================================
def process_checkout():
    """Handle checkout - requires payment_gateway to be enabled."""
    # This creates a potential conflict if new_checkout_flow is ON
    # but payment_gateway_enabled is OFF
    if is_enabled("new_checkout_flow"):
        if is_enabled("payment_gateway_enabled"):
            return "new_checkout_complete"
        else:
            # This branch is dead code if payment_gateway_enabled is always OFF
            raise RuntimeError("Payment gateway required for new checkout")
    return "legacy_checkout"


# ============================================
# Pattern 5: Class method with flag check
# ============================================
class PaymentProcessor:
    """Processes payments with feature flag controls."""
    
    def __init__(self, client: Any = None):
        self.client = client
    
    def process(self, payment: dict) -> str:
        """Process a payment."""
        if feature_flags.is_feature_enabled("premium_subscription_tier"):
            return self._premium_process(payment)
        return self._standard_process(payment)
    
    def _premium_process(self, payment: dict) -> str:
        """Premium payment processing."""
        return "premium"
    
    def _standard_process(self, payment: dict) -> str:
        """Standard payment processing."""
        return "standard"


# ============================================
# Pattern 6: Ternary expression
# ============================================
def get_theme() -> str:
    """Get theme based on dark mode flag."""
    return "dark" if is_enabled("dark_mode_enabled") else "light"


# ============================================
# Pattern 7: Assignment then check (indirect)
# ============================================
def complex_flow():
    """Example of storing flag result in variable."""
    is_premium = feature_flags.is_enabled("premium_tier")
    is_beta = feature_flags.is_enabled("beta_features")
    
    if is_premium and is_beta:
        return "premium_beta"
    elif is_premium:
        return "premium"
    elif is_beta:
        return "beta"
    return "standard"


# ============================================
# Pattern 8: Multiple flags in nested conditions
# ============================================
def render_dashboard():
    """Render dashboard with multiple flag checks."""
    if is_enabled("feature_login_v2"):
        if is_enabled("feature_dashboard_v2"):
            # Both flags must be ON
            return "full_v2_experience"
        else:
            # Only login_v2 is ON
            return "partial_v2_experience"
    
    # login_v2 is OFF
    if is_enabled("feature_analytics"):
        return "legacy_with_analytics"
    
    return "legacy_basic"


# ============================================
# Pattern 9: Flag-gated import (runtime check)
# ============================================
def get_ml_predictions(data: list) -> list:
    """Get ML predictions if feature is enabled."""
    if is_enabled("ml_predictions"):
        # Dynamically import ML module
        return ["prediction_1", "prediction_2"]
    return []
