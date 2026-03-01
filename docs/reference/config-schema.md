# Config Schema

greybeard's config lives at `~/.greybeard/config.yaml`.

## Full schema

```yaml
# Default content pack (used when --pack is not specified)
default_pack: staff-core

# Default review mode (used when --mode is not specified)
default_mode: review

llm:
  # Backend to use
  # Options: openai | anthropic | ollama | lmstudio
  backend: openai

  # Model name. Leave empty to use the backend's default.
  # openai default:         gpt-4o
  # anthropic default:      claude-3-5-sonnet-20241022
  # ollama default:         llama3.2
  # lmstudio default:       local-model
  model: ""

  # Base URL for the API. Leave empty to use the backend's default.
  # ollama default:   http://localhost:11434/v1
  # lmstudio default: http://localhost:1234/v1
  base_url: ""

  # Environment variable name to read the API key from.
  # Leave empty to use the backend's default env var.
  # openai default:         OPENAI_API_KEY
  # anthropic default:      ANTHROPIC_API_KEY
  # ollama/lmstudio:        (no key needed)
  api_key_env: ""

# Remote pack sources (future: auto-refresh on update)
pack_sources: []
```

## Default values per backend

| Backend     | Default model                | Default base URL            | API key env         |
| ----------- | ---------------------------- | --------------------------- | ------------------- |
| `openai`    | `gpt-4o`                     | (OpenAI default)            | `OPENAI_API_KEY`    |
| `anthropic` | `claude-3-5-sonnet-20241022` | (Anthropic default)         | `ANTHROPIC_API_KEY` |
| `ollama`    | `llama3.2`                   | `http://localhost:11434/v1` | (none)              |
| `lmstudio`  | `local-model`                | `http://localhost:1234/v1`  | (none)              |

## Managing config

```bash
greybeard init            # interactive setup
greybeard config show     # view current values
greybeard config set llm.backend ollama
greybeard config set llm.model llama3.2
```

## Notes

- The config file never stores API keys — only the env var name to read them from.
- Empty string values are stripped from the saved file.
- All fields are optional — sensible defaults work without a config file.
