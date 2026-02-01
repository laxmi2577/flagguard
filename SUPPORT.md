# FlagGuard Support

## Getting Help

### ðŸ“– Documentation
- [README](README.md) - Quick start guide
- [API Documentation](docs/api.md) - Detailed API reference
- [Examples](examples/) - Example configurations and code

### ðŸ’¬ Community
- [GitHub Discussions](https://github.com/laxmi2577/flagguard/discussions) - Ask questions and share ideas
- [GitHub Issues](https://github.com/laxmi2577/flagguard/issues) - Report bugs and request features

### ðŸ› Bug Reports
Before submitting a bug report:
1. Check [existing issues](https://github.com/laxmi2577/flagguard/issues)
2. Include FlagGuard version (`flagguard --version`)
3. Provide minimal reproduction steps
4. Share your configuration (anonymized if needed)

### ðŸ”’ Security Issues
For security vulnerabilities, please see [SECURITY.md](SECURITY.md).
**Do NOT open public issues for security problems.**

## Response Times

| Channel | Response Time |
|---------|---------------|
| Security Issues | < 48 hours |
| Bug Reports | < 72 hours |
| Feature Requests | 1 week |
| Questions | 1 week |

## FAQ

### Installation Issues

**Q: Z3 installation fails on Windows**
```bash
pip install z3-solver --only-binary :all:
```

**Q: tree-sitter installation fails**
```bash
pip install tree-sitter tree-sitter-python tree-sitter-javascript
```

### Usage Issues

**Q: Analysis is slow with large codebases**
- Use `--max-conflicts 50` to limit output
- Exclude test directories with patterns
- Consider running on changed files only

**Q: LLM features not working**
- Ensure Ollama is installed and running
- Check with `flagguard check-llm`
- Use `--no-llm` to skip LLM features

**Q: False positives in conflict detection**
- Review your flag dependencies
- Check if prerequisites are correctly configured
- Open an issue with your config (anonymized)

## Professional Support

For enterprise support, custom integrations, or training:
- Email: laxmiranjan444@gmail.com
