# Contributing to greybeard

Thanks for your interest in contributing! 🎉

## Quick Links

- **Full Contributing Guide**: [docs/contributing.md](docs/contributing.md)
- **Code of Conduct**: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Security Policy**: [SECURITY.md](SECURITY.md)

## Ways to Contribute

### 1. Content Packs (Easiest!)

Content packs are the highest-value contribution. Create a new perspective:

```bash
cd packs/
cp staff-core.yaml my-new-pack.yaml
# Edit your pack
git diff HEAD~1 | greybeard analyze --pack packs/my-new-pack.yaml
```

See [Pack Schema](docs/reference/pack-schema.md) for details.

### 2. Bug Reports

Found a bug? [Open an issue](https://github.com/btotharye/greybeard/issues/new?template=bug_report.yml)

### 3. Feature Requests

Have an idea? [Suggest a feature](https://github.com/btotharye/greybeard/issues/new?template=feature_request.yml)

### 4. Code Contributions

See the [full guide](docs/contributing.md) for:

- Development setup
- Running tests
- Code style
- Commit guidelines

## Quick Dev Setup

```bash
git clone https://github.com/btotharye/greybeard.git
cd greybeard
make install-dev
make test
```

## Questions?

- Check the [documentation](https://greybeard.readthedocs.io)
- Ask in [GitHub Discussions](https://github.com/btotharye/greybeard/discussions)
- Open an issue if you're stuck

---

For the full contributing guide with detailed instructions, see [docs/contributing.md](docs/contributing.md).
