# Contributing to FlagGuard

Thank you for your interest in contributing to FlagGuard! We welcome issues, pull requests, and feature requests from the community.

---

## 🛠️ Development Setup

FlagGuard uses [uv](https://github.com/astral-sh/uv) for fast, reliable package management.

```bash
# Clone the repository
git clone https://github.com/laxmi2577/flagguard.git
cd flagguard

# Install dependencies and setup environment
uv sync

# Run the test suite
uv run pytest tests/ -v
```

---

## 🧹 Code Style & Linting

We enforce strict coding standards to maintain quality.

- **Ruff**: Fast Python linter and formatter.
- **Type hints**: Required for all public APIs (Mypy).
- **Docstrings**: Required for all public classes and functions.

```bash
# Format code automatically
uv run ruff format src/ tests/

# Check for linting errors
uv run ruff check src/ tests/
```

---

## 🔁 Pull Request Process

1. **Fork** the repository instead of requesting branch access.
2. **Create a branch** for your feature: `git checkout -b feat/my-new-feature` or `fix/issue-123`.
3. **Commit** your changes following conventional commits.
4. **Write Tests**: Ensure your code is covered by `pytest`.
5. **Run Tests Locally**: `uv run pytest tests/ -v`
6. **Push and create a PR** against the `master` branch.

### Commit Message Format

```text
type(scope): short description

Longer description explaining the reasoning.

Fixes #123
```

Valid types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.

---

## 🏗️ Adding New Features

### Adding a New Parser
1. Create `src/flagguard/parsers/newformat.py`
2. Implement the `NewFormatParser` class mapping to native `FlagDefinition` models.
3. Import and explicitly register it in `src/flagguard/parsers/__init__.py`
4. Write test files in `tests/unit/test_parsers/`

### Adding a New Language Scanner
1. Verify the `tree-sitter` grammar exists (e.g., `tree-sitter-go`).
2. Add the dependency to `pyproject.toml`.
3. Create an extractor in `src/flagguard/parsers/ast/newlang.py`.
4. Add corresponding test files mapping AST paths.

---

## 🔒 Security Vulnerabilities

Please read our [SECURITY.md](../SECURITY.md) before contributing security-related changes. **Do NOT open public issues for zero-day vulnerabilities.**

---

## 💬 Getting Help

- Open a [Discussion](https://github.com/laxmi2577/flagguard/discussions) on GitHub.
- Submit bug reports via [GitHub Issues](https://github.com/laxmi2577/flagguard/issues).
