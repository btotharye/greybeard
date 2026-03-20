# Contributing to greybeard

Thanks for your interest in contributing! 🎉

## Quick Links

- **Full Contributing Guide**: [docs/contributing.md](docs/contributing.md)
- **Code of Conduct**: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Security Policy**: [SECURITY.md](SECURITY.md)

## Ways to Contribute

### 1. Content Packs (Easiest, Highest Value!)

Create a new perspective for your team or community:

```bash
cd packs/
cp staff-core.yaml my-new-pack.yaml
# Edit your pack definition
git diff HEAD~1 | greybeard analyze --pack packs/my-new-pack.yaml
```

**Pack Ideas:**
- Security engineer reviewing auth/injection/secrets
- Data engineer reviewing migrations/schemas
- Mobile engineer reviewing client/server contracts
- SRE reviewing SLOs/error budgets/toil

See [Pack Schema](docs/reference/pack-schema.md) and [Packs Guide](docs/guides/packs.md) for details.

### 2. Custom Agents (Advanced)

Build specialized decision-making tools using the framework:

```python
from greybeard.common import BaseAgent

class MyCustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="my-agent", description="...")
    
    def run(self, user_input: str) -> dict:
        context = self.research.gather_file_context("file.txt")
        response = self.llm.call(...)
        return {"result": response}
```

See [Creating Agents Guide](docs/guides/creating_agents.md) and [template](examples/custom_agent_template.py).

### 3. Interactive Mode Improvements

Enhance the stateful conversation REPL:

- New interactive commands or workflows
- Better context management for long sessions
- Improved streaming UX
- Bug fixes

See [Contributing to Interactive Mode](#contributing-to-interactive-mode) in [docs/contributing.md](docs/contributing.md).

### 4. Bug Reports

Found a bug? [Open an issue](https://github.com/btotharye/greybeard/issues/new?template=bug_report.yml) with steps to reproduce.

### 5. Feature Requests

Have an idea? [Suggest a feature](https://github.com/btotharye/greybeard/issues/new?template=feature_request.yml).

### 6. Code Contributions

See the [full guide](docs/contributing.md) for:

- Development setup
- Running tests
- Code style and formatting
- Interactive mode development
- Commit guidelines

## Quick Dev Setup

```bash
git clone https://github.com/btotharye/greybeard.git
cd greybeard
make install-dev           # Install dependencies
make pre-commit-install    # Install git hooks (recommended)
make test                  # Run tests
```

See the [full development guide](docs/contributing.md) for details on pre-commit hooks, coverage reports, type checking, and more.

## Questions?

- Check the [documentation](https://greybeard.readthedocs.io)
- Ask in [GitHub Discussions](https://github.com/btotharye/greybeard/discussions)
- Open an issue if you're stuck

---

For the full contributing guide with detailed instructions, see [docs/contributing.md](docs/contributing.md).
