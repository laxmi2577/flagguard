"""Pytest configuration and fixtures for FlagGuard tests."""

import json
from pathlib import Path
from typing import Generator

import pytest

from flagguard.core.models import (
    FlagDefinition,
    FlagType,
    FlagVariation,
)


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_launchdarkly_config(fixtures_dir: Path) -> Path:
    """Create a sample LaunchDarkly config file."""
    config_path = fixtures_dir / "configs" / "launchdarkly.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    config = {
        "flags": {
            "new_checkout": {
                "key": "new_checkout",
                "on": True,
                "variations": [True, False],
                "fallthrough": {"variation": 0},
                "prerequisites": [{"key": "payment_enabled"}],
                "description": "New checkout flow",
                "tags": ["checkout", "ui"],
            },
            "payment_enabled": {
                "key": "payment_enabled",
                "on": False,
                "variations": [True, False],
                "fallthrough": {"variation": 1},
                "description": "Payment system toggle",
            },
            "premium_tier": {
                "key": "premium_tier",
                "on": True,
                "variations": [True, False],
                "fallthrough": {"variation": 0},
                "prerequisites": [{"key": "payment_enabled"}],
            },
        }
    }
    
    config_path.write_text(json.dumps(config, indent=2))
    return config_path


@pytest.fixture
def sample_generic_config(fixtures_dir: Path) -> Path:
    """Create a sample generic JSON config file."""
    config_path = fixtures_dir / "configs" / "generic.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    config = {
        "flags": [
            {
                "name": "feature_a",
                "enabled": True,
                "type": "boolean",
            },
            {
                "name": "feature_b",
                "enabled": True,
                "type": "boolean",
                "dependencies": ["feature_a"],
            },
            {
                "name": "feature_c",
                "enabled": False,
                "type": "boolean",
            },
        ]
    }
    
    config_path.write_text(json.dumps(config, indent=2))
    return config_path


@pytest.fixture
def sample_flags() -> list[FlagDefinition]:
    """Return sample flag definitions for testing."""
    return [
        FlagDefinition(
            name="feature_parent",
            flag_type=FlagType.BOOLEAN,
            enabled=True,
            variations=[
                FlagVariation(name="on", value=True),
                FlagVariation(name="off", value=False),
            ],
        ),
        FlagDefinition(
            name="feature_child",
            flag_type=FlagType.BOOLEAN,
            enabled=True,
            dependencies=["feature_parent"],
            variations=[
                FlagVariation(name="on", value=True),
                FlagVariation(name="off", value=False),
            ],
        ),
        FlagDefinition(
            name="feature_disabled",
            flag_type=FlagType.BOOLEAN,
            enabled=False,
        ),
    ]


@pytest.fixture
def sample_python_source(fixtures_dir: Path) -> Path:
    """Create a sample Python source file with flag usages."""
    source_path = fixtures_dir / "source_code" / "python_sample" / "app.py"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    
    code = '''"""Sample application with feature flags."""

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
'''
    
    source_path.write_text(code)
    return source_path


@pytest.fixture
def sample_js_source(fixtures_dir: Path) -> Path:
    """Create a sample JavaScript source file with flag usages."""
    source_path = fixtures_dir / "source_code" / "javascript_sample" / "app.js"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    
    code = '''// Sample application with feature flags
import { isEnabled, useFlag } from "@launchdarkly/js-client-sdk";

function CheckoutComponent() {
    if (isEnabled("new_checkout")) {
        return <NewCheckout />;
    }
    return <LegacyCheckout />;
}

function PaymentHandler() {
    const paymentEnabled = useFlag("payment_enabled");
    
    if (paymentEnabled) {
        processPayment();
    }
}

const isPremium = isEnabled("premium_tier");
'''
    
    source_path.write_text(code)
    return source_path
