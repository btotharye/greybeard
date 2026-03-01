# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security issues seriously. If you discover a security vulnerability in greybeard, please report it responsibly.

### How to Report

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Instead, report security issues via email to:

**btotharye@gmail.com**

Include the following information:

- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if you have one)

### What to Expect

- **Acknowledgment**: We'll acknowledge receipt of your report within 48 hours
- **Updates**: We'll provide updates on the status of your report within 5 business days
- **Fix Timeline**: We aim to release security fixes within 7-14 days for critical issues
- **Credit**: With your permission, we'll credit you in the release notes

## Security Considerations

### API Keys

greybeard reads API keys from environment variables and never stores them in configuration files. However:

- Never commit `.env` files to version control
- Be cautious when sharing logs or error messages (they may contain API keys)
- Use appropriate file permissions for your shell profile (e.g., `chmod 600 ~/.zshrc`)

### LLM Backend Security

When using greybeard:

- **Code Review**: Be aware that your code/diffs are sent to the configured LLM backend
- **Sensitive Data**: Avoid piping sensitive information (secrets, credentials, PII) into greybeard
- **Local Backends**: For sensitive codebases, consider using local backends (Ollama, LM Studio)
- **Network Traffic**: Cloud backends (OpenAI, Anthropic) transmit data over HTTPS

### Content Packs

- Content packs are YAML files that can execute system prompts
- Only install content packs from trusted sources
- Review pack contents before installation
- Content packs can guide LLM behavior but cannot execute arbitrary code

### MCP Integration

When using greybeard as an MCP server:

- The MCP server exposes review tools to connected clients
- Ensure clients (Claude Desktop, Cursor, etc.) are from trusted sources
- MCP communication is local (stdio) by default

## Security Best Practices

1. **Keep greybeard updated**: Run `uv pip install --upgrade greybeard` regularly
2. **Use environment variables**: Store API keys in environment variables, not config files
3. **Review content packs**: Inspect pack YAML before installation
4. **Local models for sensitive code**: Use Ollama or LM Studio for proprietary/sensitive work
5. **Limit permissions**: Don't run greybeard with elevated privileges

## Dependencies

greybeard relies on several third-party dependencies. We monitor these for security issues and update them promptly.

To check for outdated dependencies:

```bash
uv pip list --outdated
```

## Questions?

If you have questions about security but don't have a vulnerability to report, feel free to open a GitHub Discussion.
