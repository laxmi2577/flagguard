"""Sample application with feature flags."""

from typing import Any


def is_enabled(flag_name: str) -> bool:
    """Check if a feature flag is enabled."""
    # This would normally call your flag provider
    return True


def checkout():
    """Handle checkout process."""
    if is_enabled("new_checkout"):
        return new_checkout_flow()
    return legacy_checkout()


def new_checkout_flow() -> str:
    """New checkout implementation."""
    if is_enabled("payment_enabled"):
        process_payment()
    return "New checkout complete"


def legacy_checkout() -> str:
    """Legacy checkout."""
    return "Legacy checkout complete"


def process_payment() -> None:
    """Process payment."""
    pass


def premium_features():
    """Handle premium features."""
    if is_enabled("premium_tier"):
        # This is dead code if payment_enabled is off
        # because premium_tier requires payment_enabled
        if is_enabled("payment_enabled"):
            return "Premium features active"
    return "Basic features"


if __name__ == "__main__":
    print(checkout())
    print(premium_features())
