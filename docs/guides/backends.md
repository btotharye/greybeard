# LLM Backends

greybeard supports multiple LLM backends. Configure once with `greybeard init` or `greybeard config set`.

---

## OpenAI

The default backend. Uses the OpenAI API.

**Setup:**

```bash
export OPENAI_API_KEY=sk-...
greybeard config set llm.backend openai
```

**Default model:** `gpt-4o`

**Other models:**

```bash
greybeard config set llm.model gpt-4o-mini       # cheaper, faster
greybeard config set llm.model gpt-4-turbo        # older but capable
```

---

## Anthropic (Claude)

Uses the Anthropic API. Requires the optional `anthropic` extra.

**Setup:**

```bash
uv pip install "greybeard[anthropic]"
export ANTHROPIC_API_KEY=sk-ant-...
greybeard config set llm.backend anthropic
```

**Default model:** `claude-3-5-sonnet-20241022`

**Other models:**

```bash
greybeard config set llm.model claude-3-5-haiku-20241022   # faster, cheaper
greybeard config set llm.model claude-3-opus-20240229       # most capable
```

---

## Ollama (local, free)

Run any open-source model locally — no API key, no cost, fully offline.

**Setup:**

1. Install [Ollama](https://ollama.ai)
2. Pull a model: `ollama pull llama3.2`
3. Start the server: `ollama serve`
4. Configure greybeard:

```bash
greybeard config set llm.backend ollama
greybeard config set llm.model llama3.2
```

**Default base URL:** `http://localhost:11434/v1`

**Good models for review tasks:**

| Model              | Size | Notes                                        |
| ------------------ | ---- | -------------------------------------------- |
| `llama3.2`         | 3B   | Fast, good for quick reviews                 |
| `llama3.1:8b`      | 8B   | Better reasoning                             |
| `llama3.1:70b`     | 70B  | Close to GPT-4 quality (needs good hardware) |
| `qwen2.5-coder:7b` | 7B   | Strong for code review                       |
| `mistral:7b`       | 7B   | Good general purpose                         |

```bash
ollama pull llama3.2
greybeard config set llm.model llama3.2
git diff main | greybeard analyze
```

!!! tip "Hiding verbose Ollama output"
Ollama prints verbose initialization logs (GPU setup, model loading, etc.) and warnings to stderr. To hide these and only see greybeard's output:

    **Option 1: Redirect stderr**
    ```bash
    git diff main | greybeard analyze 2>/dev/null
    ```

    **Option 2: Set Ollama's log level (recommended)**
    ```bash
    # Add to your ~/.zshrc or ~/.bashrc
    export OLLAMA_DEBUG=false

    # Then restart Ollama
    pkill ollama && ollama serve &
    ```

    **Option 3: Shell alias**
    ```bash
    # Add to your shell profile
    alias gb='greybeard analyze 2>/dev/null'

    # Then use:
    git diff main | gb
    ```

---

## LM Studio (local, free)

Run models locally using [LM Studio](https://lmstudio.ai)'s built-in server — no API key required.

**Setup:**

1. Download and install [LM Studio](https://lmstudio.ai)
2. Download a model from the Discover tab
3. Start the local server (Local Server tab → Start Server)
4. Configure greybeard:

```bash
greybeard config set llm.backend lmstudio
greybeard config set llm.model local-model   # LM Studio uses this as a placeholder
```

**Default base URL:** `http://localhost:1234/v1`

!!! tip
LM Studio accepts any model name — use `local-model` or whatever your loaded model is named.

---

```bash
git diff main | greybeard analyze --model gpt-4o-mini
git diff main | greybeard analyze --model llama3.1:70b
```

---

## Custom OpenAI-compatible endpoints

Any service that exposes an OpenAI-compatible API works:

```bash
greybeard config set llm.backend openai
greybeard config set llm.base_url https://my-proxy.example.com/v1
greybeard config set llm.api_key_env MY_PROXY_KEY
```
