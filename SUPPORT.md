# FlagGuard Support

## Getting Help

### Documentation
- [README](README.md) - Quick start guide and full feature reference
- [CONTRIBUTING](CONTRIBUTING.md) - Development setup and contribution guide
- [SECURITY](SECURITY.md) - Security policy and vulnerability reporting
- [CHANGELOG](CHANGELOG.md) - Version history

### API Documentation
- **Swagger UI**: Start the API server and visit `http://localhost:8000/docs`
- **ReDoc**: Alternative docs at `http://localhost:8000/redoc`

### Community
- [GitHub Discussions](https://github.com/laxmi2577/flagguard/discussions) - Ask questions and share ideas
- [GitHub Issues](https://github.com/laxmi2577/flagguard/issues) - Report bugs and request features

### Bug Reports
Before submitting a bug report:
1. Check [existing issues](https://github.com/laxmi2577/flagguard/issues)
2. Include FlagGuard version (`flagguard --version`)
3. Provide minimal reproduction steps
4. Share your configuration (anonymized if needed)

### Security Issues
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

**Q: API server won't start (port in use)**
```bash
# Find and kill the process using port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

## Professional Support

For enterprise support, custom integrations, or training:
- Email: laxmiranjan444@gmail.com
