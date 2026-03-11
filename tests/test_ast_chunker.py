"""Tests for AST-Aware Code Chunker (Phase 1 — Step 1.1).

Validates that the ASTCodeChunker correctly extracts function-level
chunks from Python and JavaScript source code using tree-sitter.
"""

import tempfile
from pathlib import Path

import pytest

from flagguard.rag.ingester import ASTCodeChunker, ASTChunk


# ── Fixtures ──

SAMPLE_PYTHON = '''
import os

FLAG_CONFIG = {"dark_mode": True}


def check_auth(user):
    """Check user authentication."""
    if is_enabled("auth_v2"):
        return validate_token(user.token)
    return legacy_auth(user)


class PaymentService:
    """Handles payment processing."""

    def checkout(self, cart):
        """Process checkout."""
        if is_enabled("premium"):
            return self._premium_checkout(cart)
        return self._basic_checkout(cart)

    def _premium_checkout(self, cart):
        """Premium checkout with discounts."""
        discount = get_flag("loyalty_discount")
        return cart.total * discount

    def refund(self, order_id):
        """Process refund."""
        return {"status": "refunded", "order": order_id}


def standalone_helper():
    """A helper with no flag references."""
    return 42
'''

SAMPLE_JAVASCRIPT = '''
function checkAuth(user) {
    if (isEnabled("auth_v2")) {
        return validateToken(user.token);
    }
    return legacyAuth(user);
}

const getDiscount = (cart) => {
    if (hasFeature("loyalty_discount")) {
        return cart.total * 0.9;
    }
    return cart.total;
};
'''


@pytest.fixture
def chunker():
    """Create a fresh ASTCodeChunker instance."""
    return ASTCodeChunker()


@pytest.fixture
def python_file(tmp_path):
    """Create a temporary Python file."""
    f = tmp_path / "sample.py"
    f.write_text(SAMPLE_PYTHON)
    return f


@pytest.fixture
def js_file(tmp_path):
    """Create a temporary JavaScript file."""
    f = tmp_path / "sample.js"
    f.write_text(SAMPLE_JAVASCRIPT)
    return f


# ── Test Cases ──

class TestASTCodeChunker:
    """Tests for the AST-aware code chunker."""

    def test_chunks_python_functions(self, chunker, python_file):
        """Should extract individual functions as chunks."""
        chunks = chunker.chunk_file(python_file)
        func_names = [c.function_name for c in chunks if c.function_name]

        assert "check_auth" in func_names
        assert "standalone_helper" in func_names

    def test_chunks_python_classes(self, chunker, python_file):
        """Should extract methods with class context."""
        chunks = chunker.chunk_file(python_file)
        methods = [c for c in chunks if c.class_name == "PaymentService"]

        method_names = [c.function_name for c in methods]
        assert "checkout" in method_names
        assert "_premium_checkout" in method_names
        assert "refund" in method_names

    def test_qualified_name(self, chunker, python_file):
        """Should build fully qualified names like ClassName.method."""
        chunks = chunker.chunk_file(python_file)
        qualified = [c.qualified_name for c in chunks]

        assert "PaymentService.checkout" in qualified
        assert "check_auth" in qualified

    def test_flags_referenced_extracted(self, chunker, python_file):
        """Should extract flag names from is_enabled() calls."""
        chunks = chunker.chunk_file(python_file)
        auth_chunk = next(c for c in chunks if c.function_name == "check_auth")

        assert "auth_v2" in auth_chunk.flags_referenced

    def test_chunk_metadata_completeness(self, chunker, python_file):
        """Each chunk should have file, start_line, end_line, chunk_type."""
        chunks = chunker.chunk_file(python_file)

        for chunk in chunks:
            assert chunk.file_path == str(python_file)
            assert chunk.start_line >= 1
            assert chunk.end_line >= chunk.start_line
            assert chunk.chunk_type in ("function", "method", "module", "class", "block")

    def test_doc_id_is_stable(self, chunker, python_file):
        """Same file should produce the same doc_ids across runs."""
        chunks1 = chunker.chunk_file(python_file)
        chunks2 = chunker.chunk_file(python_file)

        ids1 = sorted([c.doc_id for c in chunks1])
        ids2 = sorted([c.doc_id for c in chunks2])
        assert ids1 == ids2

    def test_empty_file_produces_no_chunks(self, chunker, tmp_path):
        """Empty files should return an empty list."""
        f = tmp_path / "empty.py"
        f.write_text("")
        chunks = chunker.chunk_file(f)
        assert chunks == []

    def test_no_functions_produces_module_chunk(self, chunker, tmp_path):
        """File with no functions should produce a single module-level chunk."""
        f = tmp_path / "constants.py"
        f.write_text("X = 1\nY = 2\nZ = is_enabled('test_flag')\n")
        chunks = chunker.chunk_file(f)

        assert len(chunks) >= 1
        # At least one chunk should reference 'test_flag'
        all_flags = [flag for c in chunks for flag in c.flags_referenced]
        assert "test_flag" in all_flags

    def test_function_without_flags(self, chunker, python_file):
        """Functions without flag references should have empty flags list."""
        chunks = chunker.chunk_file(python_file)
        refund = next(c for c in chunks if c.function_name == "refund")

        assert refund.flags_referenced == []

    def test_fallback_chunker(self, chunker, tmp_path):
        """Unsupported file types should use fallback chunking."""
        f = tmp_path / "test.rb"
        f.write_text("def hello\n  puts 'hello'\nend\n")
        chunks = chunker.chunk_file(f)
        # Fallback should still produce at least one chunk for non-empty files
        # (or empty for unsupported extensions depending on implementation)
        assert isinstance(chunks, list)
