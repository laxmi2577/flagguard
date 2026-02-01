# FlagGuard Roadmap

## Current Version: 0.1.0

### ✅ Completed Features
- SAT-based conflict detection
- Dead code detection
- LaunchDarkly/Unleash parsers
- Python/JavaScript source scanning
- CLI and Web UI
- GitHub Action
- LLM explanations (Ollama)

---

## Upcoming Releases

### v0.2.0 - Language Expansion (Month 2)
- [ ] Go language support
- [ ] Java language support
- [ ] TypeScript improved support
- [ ] ConfigCat config format
- [ ] Split.io config format
- [ ] Custom flag patterns

### v0.3.0 - Performance & DX (Month 3)
- [ ] Incremental analysis (changed files only)
- [ ] AST caching for faster re-runs
- [ ] VS Code extension (basic)
- [ ] GitLab CI template
- [ ] Improved error messages

### v0.4.0 - Enterprise Features (Month 4)
- [ ] SARIF output for GitHub Security
- [ ] Ignore rules (suppress false positives)
- [ ] Multi-repository analysis
- [ ] Historical trend tracking
- [ ] Team/org configuration

### v1.0.0 - Stable Release (Month 6)
- [ ] API stability guarantee
- [ ] Migration guide from 0.x
- [ ] Comprehensive test suite
- [ ] Performance benchmarks
- [ ] SLA for bug fixes

---

## Future Ideas (Backlog)

| Feature | Priority | Effort | Status |
|---------|----------|--------|--------|
| Rust/C++ support | P3 | High | Backlog |
| Runtime integration | P2 | High | Backlog |
| OpenAI API option | P3 | Low | Backlog |
| Slack notifications | P3 | Low | Backlog |
| Visual diff tool | P2 | Medium | Backlog |
| Self-hosted SaaS | P2 | High | Backlog |

---

## How to Contribute

Want to help with a roadmap item?

1. Check if there's an open issue for the feature
2. Comment on the issue to express interest
3. Wait for maintainer approval
4. Submit a PR following [CONTRIBUTING.md](CONTRIBUTING.md)

## Suggest Features

Have an idea not on the roadmap?

1. Open a [Feature Request](https://github.com/yourusername/flagguard/issues/new?template=feature_request.yml)
2. Describe the problem it solves
3. Propose a solution
4. Community votes help prioritize!
