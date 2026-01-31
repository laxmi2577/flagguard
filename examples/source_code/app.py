"""Example Python application with feature flag usage.

This file demonstrates various feature flag patterns that
FlagGuard can detect and analyze.
"""

from typing import Any

# Mock feature flag client
class FeatureFlags:
    """Mock feature flag client for demonstration."""
    
    @staticmethod
    def is_enabled(flag_name: str) -> bool:
        """Check if a flag is enabled."""
        return False  # Mock implementation
    
    @staticmethod
    def variation(flag_name: str, default: Any) -> Any:
        """Get a flag variation value."""
        return default


feature_flags = FeatureFlags()


# --- CONFLICT EXAMPLE ---
# payment_gateway_enabled is OFF, but these features require it

def process_checkout():
    """Handle checkout flow."""
    # This flag requires payment_gateway_enabled, which is OFF
    if feature_flags.is_enabled("new_checkout_flow"):
        # This code is DEAD - can never execute
        return process_new_checkout()
    else:
        return process_legacy_checkout()


def get_subscription_tier():
    """Get user subscription tier."""
    # This also requires payment_gateway_enabled
    if feature_flags.is_enabled("premium_subscription_tier"):
        # This code is also DEAD
        return "premium"
    return "free"


# --- HEALTHY FLAG USAGE ---

def render_theme():
    """Render UI with appropriate theme."""
    # This flag has no dependencies
    if feature_flags.is_enabled("dark_mode_enabled"):
        return apply_dark_theme()
    else:
        return apply_light_theme()


def render_homepage():
    """Render homepage based on A/B test."""
    variant = feature_flags.variation("ab_test_homepage", "control")
    
    if variant == "control":
        return render_control_homepage()
    elif variant == "variant_a":
        return render_variant_a_homepage()
    elif variant == "variant_b":
        return render_variant_b_homepage()
    else:
        return render_control_homepage()


# --- NEGATED FLAG CHECK ---

def show_upgrade_prompt():
    """Show upgrade prompt to non-premium users."""
    # Negated check - shows prompt when NOT premium
    if not feature_flags.is_enabled("premium_subscription_tier"):
        display_upgrade_banner()


# --- NESTED FLAG CHECKS ---

def complex_flow():
    """Example of nested flag checks."""
    if feature_flags.is_enabled("feature_login_v2"):
        if feature_flags.is_enabled("feature_dashboard_v2"):
            # Both flags must be true
            return render_new_experience()
        else:
            return render_partial_experience()
    return render_legacy_experience()


# Mock implementations
def process_new_checkout(): pass
def process_legacy_checkout(): pass
def apply_dark_theme(): pass
def apply_light_theme(): pass
def render_control_homepage(): pass
def render_variant_a_homepage(): pass
def render_variant_b_homepage(): pass
def display_upgrade_banner(): pass
def render_new_experience(): pass
def render_partial_experience(): pass
def render_legacy_experience(): pass
