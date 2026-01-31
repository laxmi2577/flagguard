# Contributing to FlagGuard

Thank you for your interest in contributing to FlagGuard! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- (Optional) Ollama for LLM features

### Clone and Install

```bash
git clone https://github.com/yourusername/flagguard.git
cd flagguard
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src/flagguard --cov-report=html

# Specific test file
pytest tests/unit/test_parsers.py -v
```

### Code Quality

```bash
# Linting
ruff check src tests

# Formatting
ruff format src tests

# Type checking
mypy src
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes

- Write clean, documented code
- Add tests for new functionality
- Update documentation as needed

### 3. Run Quality Checks

```bash
ruff check src tests
ruff format src tests
mypy src
pytest
```

### 4. Commit

Use conventional commit messages:

```
feat: add support for Split.io configuration
fix: handle empty targeting rules gracefully
docs: update CLI usage examples
test: add unit tests for path analyzer
```

### 5. Submit Pull Request

- Provide a clear description
- Reference any related issues
- Ensure all checks pass

## Project Structure

```
flagguard/
├── src/flagguard/
│   ├── core/           # Data models, logging utilities
│   ├── parsers/        # Configuration parsers
│   │   └── ast/        # Source code parsers
│   ├── analysis/       # SAT solver, conflict detection
│   ├── llm/            # LLM integration
│   ├── reporters/      # Output formatters
│   ├── cli/            # CLI commands
│   └── ui/             # Web interface
├── tests/
│   ├── fixtures/       # Test data
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
└── docs/               # Documentation
```

## Adding a New Parser

1. Create `src/flagguard/parsers/newplatform.py`
2. Inherit from `BaseParser`
3. Implement the `parse()` method
4. Register in `factory.py`
5. Add tests in `tests/unit/test_parsers.py`

Example:

```python
class NewPlatformParser(BaseParser):
    def parse(self, content: str) -> list[FlagDefinition]:
        # Parse content and return FlagDefinition list
        pass
```

## Adding a New Language Extractor

1. Create `src/flagguard/parsers/ast/newlang.py`
2. Follow the pattern of `python.py` or `javascript.py`
3. Register in `scanner.py`
4. Add tests with fixture files

## Code Style

- Use type hints for all function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and small
- Use descriptive variable names

## Questions?

Open an issue for discussion before starting large changes!

---

*Thank you for contributing!*
