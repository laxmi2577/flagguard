"""Tests for Knowledge Graph (Phase 1 — Step 1.2).

Validates that the CodeKnowledgeGraph correctly builds a directed
call graph, tracks flag references, and performs transitive impact analysis.
"""

import tempfile
from pathlib import Path

import pytest

from flagguard.ai.graph import CodeKnowledgeGraph, FunctionNode


# ── Fixtures ──

SAMPLE_CODEBASE = {
    "auth.py": '''
def validate_token(token):
    """Validate a JWT token."""
    return token.is_valid


def check_auth(user):
    """Check if user is authenticated."""
    if is_enabled("auth_v2"):
        return validate_token(user.token)
    return False
''',
    "billing.py": '''
def apply_discount(cart, rate):
    """Apply a discount to the cart."""
    return cart.total * rate


def checkout(cart, user):
    """Main checkout flow."""
    check_auth(user)
    if is_enabled("premium"):
        apply_discount(cart, 0.1)
    return process_payment(cart)


def process_payment(cart):
    """Process the payment."""
    return {"status": "paid", "amount": cart.total}
''',
    "notifications.py": '''
def send_email(user, msg):
    """Send an email notification."""
    if is_enabled("email_v2"):
        return async_send(user.email, msg)
    return sync_send(user.email, msg)
''',
}


@pytest.fixture
def codebase_dir(tmp_path):
    """Create a temporary codebase directory."""
    for filename, content in SAMPLE_CODEBASE.items():
        f = tmp_path / filename
        f.write_text(content)
    return tmp_path


@pytest.fixture
def graph(codebase_dir):
    """Build a knowledge graph from the sample codebase."""
    g = CodeKnowledgeGraph()
    g.build_from_directory(codebase_dir)
    return g


# ── Test Cases ──

class TestCodeKnowledgeGraph:
    """Tests for the Knowledge Graph construction and traversal."""

    def test_graph_has_nodes(self, graph):
        """Graph should contain function nodes."""
        assert graph.graph.number_of_nodes() > 0

    def test_functions_detected(self, graph):
        """All functions in the sample code should be detected."""
        nodes = set(graph.graph.nodes())

        assert "check_auth" in nodes
        assert "validate_token" in nodes
        assert "checkout" in nodes
        assert "apply_discount" in nodes
        assert "process_payment" in nodes
        assert "send_email" in nodes

    def test_call_edges_created(self, graph):
        """Call edges should exist (e.g., checkout → check_auth)."""
        # checkout() calls check_auth()
        assert graph.graph.has_edge("checkout", "check_auth")
        # checkout() calls apply_discount()
        assert graph.graph.has_edge("checkout", "apply_discount")
        # checkout() calls process_payment()
        assert graph.graph.has_edge("checkout", "process_payment")
        # check_auth() calls validate_token()
        assert graph.graph.has_edge("check_auth", "validate_token")

    def test_flag_references(self, graph):
        """Functions that check flags should have them in metadata."""
        check_auth_data = graph.graph.nodes["check_auth"]
        assert "auth_v2" in check_auth_data.get("flags", [])

        checkout_data = graph.graph.nodes["checkout"]
        assert "premium" in checkout_data.get("flags", [])

    def test_get_functions_using_flag(self, graph):
        """Should find functions that directly reference a flag."""
        auth_funcs = graph.get_functions_using_flag("auth_v2")
        auth_names = [f.qualified_name for f in auth_funcs]

        assert "check_auth" in auth_names

    def test_get_transitive_callers(self, graph):
        """Should find all upstream callers of a function."""
        callers = graph.get_transitive_callers("validate_token")
        caller_names = [c.qualified_name for c in callers]

        # checkout() → check_auth() → validate_token()
        assert "check_auth" in caller_names
        assert "checkout" in caller_names

    def test_get_impact_for_flag(self, graph):
        """Should find ALL impacted functions (direct + transitive)."""
        impacted = graph.get_impact_for_flag("auth_v2")
        impacted_names = [f.qualified_name for f in impacted]

        # Direct: check_auth references auth_v2
        assert "check_auth" in impacted_names
        # Transitive: checkout calls check_auth
        assert "checkout" in impacted_names

    def test_isolated_function_not_in_impact(self, graph):
        """Functions not connected to the flag should NOT be impacted."""
        impacted = graph.get_impact_for_flag("auth_v2")
        impacted_names = [f.qualified_name for f in impacted]

        # send_email is isolated and uses email_v2, not auth_v2
        assert "send_email" not in impacted_names

    def test_graph_stats(self, graph):
        """Graph stats should be reasonable."""
        stats = graph.get_graph_stats()

        assert stats["total_functions"] >= 6
        assert stats["total_call_edges"] >= 4
        assert stats["functions_with_flags"] >= 3

    def test_empty_directory(self, tmp_path):
        """Empty directory should produce an empty graph."""
        g = CodeKnowledgeGraph()
        count = g.build_from_directory(tmp_path)
        assert count == 0
        assert g.graph.number_of_nodes() == 0

    def test_nonexistent_flag_returns_empty(self, graph):
        """Querying for a non-existent flag should return empty list."""
        result = graph.get_functions_using_flag("nonexistent_flag_xyz")
        assert result == []
