# Configuration

greybeard stores its config at `~/.greybeard/config.yaml`.

## Interactive setup

```bash
greybeard init
```

## View current config

```bash
greybeard config show
```

## Set a value

```bash
greybeard config set <key> <value>
```

### Available keys

| Key               | Description                            | Example                                     |
| ----------------- | -------------------------------------- | ------------------------------------------- |
| `llm.backend`     | LLM backend to use                     | `openai`, `anthropic`, `ollama`, `lmstudio` |
| `llm.model`       | Model name (overrides backend default) | `gpt-4o-mini`, `llama3.2`                   |
| `llm.base_url`    | Custom API base URL                    | `http://localhost:11434/v1`                 |
| `llm.api_key_env` | Env var to read API key from           | `MY_OPENAI_KEY`                             |
| `default_pack`    | Default content pack                   | `staff-core`, `oncall-future-you`           |
| `default_mode`    | Default review mode                    | `review`, `mentor`, `self-check`, `coach`   |

### Examples

```bash
# Switch to Ollama (local, free)
greybeard config set llm.backend ollama
greybeard config set llm.model llama3.2

# Use a cheaper OpenAI model
greybeard config set llm.backend openai
greybeard config set llm.model gpt-4o-mini

# Default to mentor mode
greybeard config set default_mode mentor

# Default to on-call pack
greybeard config set default_pack oncall-future-you
```

## Config file reference

```yaml
# ~/.greybeard/config.yaml

default_pack: staff-core # default content pack
default_mode: review # default review mode

llm:
  backend: openai # openai | anthropic | ollama | lmstudio
  model: gpt-4o # leave empty to use the backend's default
  base_url: "" # leave empty to use the backend's default
  api_key_env: OPENAI_API_KEY # env var name (not the key itself)

pack_sources: [] # remote sources to keep synced (future feature)
```

## API keys

greybeard reads API keys from environment variables — it never stores them in the config file.

```bash
# Set in your shell profile (~/.bashrc, ~/.zshrc, etc.)
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
```

Or use a `.env` file in the directory where you run greybeard:

```bash
# .env
OPENAI_API_KEY=sk-...
```

!!! note "Local backends"
Ollama and LM Studio don't require an API key — just a running server.
