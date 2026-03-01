# CLI Reference

## Global options

```
greybeard [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show version and exit.
  --help     Show help and exit.
```

---

## `greybeard analyze`

Review a decision, diff, or document.

```
Usage: greybeard analyze [OPTIONS]

Options:
  -m, --mode [review|mentor|coach|self-check]
                    Review mode. Default: from config (usually 'review').
  -p, --pack TEXT   Content pack name or path. Default: from config.
  -r, --repo PATH   Path to a repository for context (README, git log, structure).
  -c, --context TEXT
                    Additional context notes.
  --model TEXT      Override LLM model for this run.
  -a, --audience [team|peers|leadership|customer]
                    Audience (used with --mode coach).
  -o, --output TEXT Save review to a markdown file.
  --help            Show help and exit.
```

**Examples:**

```bash
# Review a git diff with defaults
git diff main | greybeard analyze

# Mentor mode with a specific pack
git diff main | greybeard analyze --mode mentor --pack oncall-future-you

# Review a design doc and save output
cat design.md | greybeard analyze --output review.md

# Include repo context
greybeard analyze --repo . --context "mid-sprint auth migration"

# Override model for this run
git diff main | greybeard analyze --model gpt-4o-mini
```

---

## `greybeard self-check`

Review your own decision before sharing it.

```
Usage: greybeard self-check [OPTIONS]

Options:
  -c, --context TEXT  The decision or proposal to self-check. [required]
  -p, --pack TEXT     Content pack name or path.
  --model TEXT        Override LLM model.
  -o, --output TEXT   Save to a markdown file.
  --help              Show help and exit.
```

**Examples:**

```bash
greybeard self-check --context "We're migrating auth to a new provider mid-sprint"

cat proposal.md | greybeard self-check --context "Replacing our job queue"
```

---

## `greybeard coach`

Get help communicating a concern or decision constructively.

```
Usage: greybeard coach [OPTIONS]

Options:
  -a, --audience [team|peers|leadership|customer]
                    Who you're communicating with. [required]
  -c, --context TEXT
                    The concern or decision to communicate.
  -p, --pack TEXT   Content pack (default: mentor-mode).
  --model TEXT      Override LLM model.
  -o, --output TEXT Save to a markdown file.
  --help            Show help and exit.
```

**Examples:**

```bash
greybeard coach --audience leadership --context "I think we're shipping too fast"

cat concern.md | greybeard coach --audience team
```

---

## `greybeard packs`

List all available content packs (built-in and installed).

```
Usage: greybeard packs [OPTIONS]

Options:
  --help  Show help and exit.
```

---

## `greybeard pack`

Manage content packs.

### `greybeard pack install`

```
Usage: greybeard pack install [OPTIONS] SOURCE

Arguments:
  SOURCE  Pack source. Formats:
            github:owner/repo
            github:owner/repo/path/to/pack.yaml
            https://example.com/pack.yaml

Options:
  --force  Re-download even if already cached.
  --help   Show help and exit.
```

### `greybeard pack list`

```
Usage: greybeard pack list [OPTIONS]

Options:
  --help  Show help and exit.
```

### `greybeard pack remove`

```
Usage: greybeard pack remove [OPTIONS] SOURCE_SLUG

Arguments:
  SOURCE_SLUG  The source directory name under ~/.greybeard/packs/
               (visible in `greybeard pack list`).

Options:
  --help  Show help and exit.
```

---

## `greybeard config`

View and manage configuration.

### `greybeard config show`

```
Usage: greybeard config show [OPTIONS]

Options:
  --help  Show help and exit.
```

### `greybeard config set`

```
Usage: greybeard config set [OPTIONS] KEY VALUE

Arguments:
  KEY    Config key. One of:
           llm.backend      openai | anthropic | ollama | lmstudio
           llm.model        e.g. gpt-4o, claude-3-5-sonnet-20241022, llama3.2
           llm.base_url     e.g. http://localhost:11434/v1
           llm.api_key_env  e.g. OPENAI_API_KEY
           default_pack     e.g. staff-core
           default_mode     review | mentor | coach | self-check
  VALUE  The value to set.

Options:
  --help  Show help and exit.
```

---

## `greybeard init`

Interactive setup wizard. Configures LLM backend and saves to `~/.greybeard/config.yaml`.

```
Usage: greybeard init [OPTIONS]

Options:
  --help  Show help and exit.
```

---

## `greybeard mcp`

Start a stdio MCP server for use with Claude Desktop, Cursor, Zed, etc.

```
Usage: greybeard mcp [OPTIONS]

Options:
  --help  Show help and exit.
```

See [MCP Integration](../guides/mcp.md) for setup instructions.
