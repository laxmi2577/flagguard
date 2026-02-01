"""Sample application with feature flags."""

from feature_flags import is_enabled, variation

def checkout_flow():
    """Handle checkout process."""
    if is_enabled("new_checkout"):
        # New checkout logic
        process_new_checkout()
    else:
        # Legacy checkout
        process_legacy_checkout()
    
    if is_enabled("payment_enabled"):
        process_payment()

def premium_features():
    """Handle premium features."""
    if is_enabled("premium_tier"):
        show_premium_content()
    
    # Negated check
    if not is_enabled("feature_disabled"):
        show_default_content()

class FeatureManager:
    """Manages feature flags."""
    
    def check_feature(self, name: str) -> bool:
        return is_enabled(name)
    
    def get_variant(self):
        return variation("ab_test_variant", "control")
