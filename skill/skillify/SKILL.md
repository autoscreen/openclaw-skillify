---
name: skillify
description: "Generate OpenClaw/nanobot skills from any API surface. Discover APIs from OpenAPI specs, GraphQL schemas, HTML documentation, or Python packages, then generate well-structured skills with proper frontmatter, progressive disclosure, and helper scripts. Use when: (1) creating skills for a new API, (2) converting API docs to agent skills, (3) bulk-generating skills from an OpenAPI spec, or (4) the user asks to turn an API into skills."
metadata: {"nanobot":{"emoji":"🔧","requires":{"bins":["skillify"]}}}
---

# Skillify

Generate OpenClaw skills from API surfaces.

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
- `-m, --model`: LLM model for AI-aided steps. Default: reads from `SKILLIFY_MODEL` env var.
- `--install`: Copy generated skills to nanobot workspace.

## Tips

- For large APIs (100+ endpoints), review the spec JSON and adjust groupings before generating.
- Generated skills use `$ENV_VAR` references for API keys — never hardcoded secrets.
- After installing skills, start a new nanobot session to load them.
