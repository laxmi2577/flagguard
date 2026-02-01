# Contributing to FlagGuard

Thank you for your interest in contributing to FlagGuard! ðŸŽ‰

## Development Setup

```bash
# Clone the repository
git clone https://github.com/laxmi2577/flagguard.git
cd flagguard

# Install uv (if not already installed)
pip install uv

# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v
```

## Code Style

We use:
- **Ruff** for linting and formatting
- **Type hints** for all public APIs
- **Docstrings** for all public functions

```bash
# Format code
uv run ruff format src/ tests/

# Check linting
uv run ruff check src/ tests/
```

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** for your feature: `git checkout -b feature/my-feature`
3. **Make changes** and add tests
4. **Run tests**: `uv run pytest tests/ -v`
5. **Commit** with a descriptive message
6. **Push** and create a Pull Request

### Commit Message Format

```
type: short description

Longer description if needed.

Fixes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src/flagguard --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_sat_solver.py -v
```

## Adding a New Parser

1. Create `src/flagguard/parsers/newformat.py`
2. Implement `NewFormatParser` class with `parse()` method
3. Register in `src/flagguard/parsers/__init__.py`
4. Add tests in `tests/unit/test_parsers/`

## Adding a New Language

1. Install grammar: `tree-sitter-newlang`
2. Create `src/flagguard/parsers/ast/newlang.py`
3. Implement `NewLangFlagExtractor` class
4. Register in `src/flagguard/parsers/ast/__init__.py`

## Security

Please read [SECURITY.md](SECURITY.md) before contributing security-related changes.

## Questions?

- Open a [Discussion](https://github.com/laxmi2577/flagguard/discussions)
- Check existing [Issues](https://github.com/laxmi2577/flagguard/issues)

Thank you for contributing! ðŸš©
