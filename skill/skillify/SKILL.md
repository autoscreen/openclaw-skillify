---
name: skillify
description: "Generate OpenClaw/nanobot skills from any API surface, and manage API keys for those skills. Discover APIs from OpenAPI specs, GraphQL schemas, HTML documentation, or Python packages, then generate well-structured skills with proper frontmatter, progressive disclosure, and helper scripts. Use when: (1) creating skills for a new API, (2) converting API docs to agent skills, (3) bulk-generating skills from an OpenAPI spec, (4) the user asks to turn an API into skills, or (5) the user wants to set, list, or remove an API key for a skill."
metadata: {"nanobot":{"emoji":"🔧","requires":{"bins":["skillify"]}}}
---

# Skillify

Generate OpenClaw skills from API surfaces.

## First-Time Setup

Before generating skills, an LLM API key must be configured. Check if one is already stored:

```bash
skillify keys list
```

If no LLM key is stored (e.g., `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`), ask the user for one and store it:

```bash
skillify keys set OPENROUTER_API_KEY "sk-or-v1-..."
```

Skillify auto-detects which provider to use based on which key is stored. To override the model:

```bash
skillify keys set SKILLIFY_MODEL "openrouter/anthropic/claude-sonnet-4-5"
```

## Quick Start

Discover and generate in one step:

```bash
skillify run "https://api.example.com/openapi.json" -o ~/.nanobot/workspace/skills/ --install
```

## Step-by-Step Workflow

### 1. Discover the API

```bash
skillify discover <source> -o spec.json
```

Sources can be:
- OpenAPI/Swagger spec URL or file path
- GraphQL endpoint URL (must contain "graphql" in the URL)
- HTML/Markdown documentation URL or file
- Python package name (e.g., `stripe`)

### 2. Review and Edit the Spec

The spec JSON is human-editable. Adjust groupings, rename skills, or remove endpoints before generating.

### 3. Generate Skills

```bash
skillify generate spec.json -o ./skills/
```

Add `--preview` to see what would be generated without writing files.

Add `--install` to copy directly to `~/.nanobot/workspace/skills/`.

## Options

- `-t, --source-type`: Force source type (`openapi`, `graphql`, `html`, `python`). Default: auto-detect.
- `-m, --model`: LLM model for AI-aided steps.
- `--base-url`: Override the discovered API base URL.
- `--install`: Copy generated skills to nanobot workspace.

## API Key Management

Skillify stores all configuration in `~/.nanobot/workspace/keys.json`. This includes:
- **LLM keys** used by skillify itself (e.g., `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`)
- **Model override** (`SKILLIFY_MODEL`) to control which LLM model skillify uses
- **Service keys** used by generated skills at runtime (e.g., `YUTORI_API_KEY`)

Skillify auto-detects the provider and model from whichever LLM key is stored. Environment variables always take precedence over stored keys.

### Store a key

```bash
skillify keys set OPENROUTER_API_KEY "sk-or-v1-..."
skillify keys set YUTORI_API_KEY "yt_abc123..."
```

### List stored keys (masked)

```bash
skillify keys list
```

### Retrieve a key

```bash
skillify keys get YUTORI_API_KEY
```

### Remove a key

```bash
skillify keys remove YUTORI_API_KEY
```

## Tips

- Before generating, always check `skillify keys list` to ensure an LLM API key is configured.
- For large APIs (100+ endpoints), review the spec JSON and adjust groupings before generating.
- Generated skills load API keys from `~/.nanobot/workspace/keys.json` — use `skillify keys set` to configure them.
- After installing skills, start a new nanobot session to load them.
