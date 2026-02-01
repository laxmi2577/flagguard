# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Design

FlagGuard is designed with security in mind:

### Input Handling
- âœ… JSON/YAML parsing uses `json.loads()` and `yaml.safe_load()` only
- âœ… No `eval()` or `exec()` on user input
- âœ… Flag names treated as opaque strings (never executed)
- âœ… Path traversal protection in source scanning

### Data Privacy
- âœ… **Offline-first**: All processing happens locally
- âœ… **No telemetry**: No data sent to external servers
- âœ… **No storage**: Source code is never persisted
- âœ… **Air-gapped**: Works without internet connection

### LLM Security
- âœ… LLM features are optional
- âœ… User data clearly separated in prompts
- âœ… LLM output is informational only
- âœ… Local LLM (Ollama) by default

## Reporting a Vulnerability

If you discover a security vulnerability, please:

1. **DO NOT** open a public issue
2. Email security concerns to: laxmiranjan444@gmail.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 1 week
- **Fix timeline**: Depends on severity
  - Critical: 24-48 hours
  - High: 1 week
  - Medium: 2 weeks
  - Low: Next release

## Security Best Practices for Users

### CI/CD Integration

```yaml
# Fail-safe: Don't block deploys if FlagGuard crashes
- name: Run FlagGuard
  continue-on-error: true
  run: flagguard analyze --config flags.json --source ./src --no-llm
```

### Recommended Configuration

```yaml
# .flagguard.yaml
analysis:
  max_flags: 100      # Prevent DoS
  max_conflicts: 100  # Limit output size

llm:
  enabled: false      # Disable in CI for faster, deterministic results
```

### Sensitive Files

FlagGuard automatically skips:
- `.env` files
- `*.key`, `*.pem` files
- `.git` directory
- `node_modules`

## Dependency Security

We use:
- **Dependabot** for automated updates
- **pip-audit** in CI for vulnerability scanning
- **Bandit** for Python security linting
- **CodeQL** for advanced analysis

## Threat Model

| Threat | Risk | Mitigation |
|--------|------|------------|
| Malicious config | Low | Safe parsing only |
| Path traversal | Low | Path validation |
| LLM prompt injection | Low | LLM is informational only |
| Dependency vulnerabilities | Medium | Automated scanning |
