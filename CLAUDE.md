# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**openclaw-skillify** converts any API surface into OpenClaw/nanobot skills. It discovers endpoints from OpenAPI, GraphQL, HTML docs, or Python packages, groups them logically, and generates skill directories (SKILL.md + references + scripts) for AI agent use.

## Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_models.py

# Run a single test by name
pytest -k "test_endpoint_serialization"

# Run with verbose output
pytest -v

# Build package
python -m build
```

No linter/formatter is configured in the project.

## Architecture

The system has two main pipelines connected by an intermediate `APISpec` JSON representation (allowing human editing between steps):

### Discovery Pipeline (`src/skillify/discover/`)
`CLI → discover() → DiscoverySource subclass → AIAnalyzer → APISpec`

- `base.py`: `DiscoverySource` ABC — all discoverers implement `discover()` and `can_handle()`
- Auto-detection tries sources in priority order: OpenAPI → GraphQL → Python package → HTML docs (fallback)
- Each discoverer returns standardized `Endpoint` models
- `ai_analyzer.py` uses LLM to group ungrouped endpoints

### Generation Pipeline (`src/skillify/generate/`)
`APISpec → Planner → SkillWriter + ReferenceWriter + ScriptWriter → SkillOutput`

- `planner.py`: Decides inline (≤8 endpoints) vs progressive disclosure (separate `references/` files)
- `skill_writer.py`: Generates SKILL.md with YAML frontmatter
- `reference_writer.py`: Creates `references/endpoints.md` for large groups
- `script_writer.py`: Creates `scripts/auth_setup.sh` for OAuth2 flows
- `validator.py`: Validates SKILL.md structure post-generation

### LLM Integration (`src/skillify/llm/`)
- `client.py`: `SkillifyLLM` wraps litellm; default model `anthropic/claude-sonnet-4-5`, overridable via `--model` flag or `SKILLIFY_MODEL` env var
- `prompts.py`: System prompts for AI-aided grouping, description, and emoji selection

### Core Models (`src/skillify/models.py`)
All Pydantic v2: `APISpec`, `Endpoint`, `EndpointGroup`, `SkillOutput`, `AuthSpec`, `GenerationResult`

### CLI (`src/skillify/cli.py`)
Typer commands: `discover`, `generate`, `preview` (alias), `run` (both steps combined)

## Key Conventions

- **Async-first**: All discovery and generation operations use async/await (httpx.AsyncClient, litellm acompletion)
- **Testing**: pytest with pytest-asyncio (auto mode); respx for HTTP mocking; fixtures in `tests/fixtures/`
- **Skill format**: Each skill is a directory with `SKILL.md` (YAML frontmatter with embedded JSON metadata), optional `references/`, optional `scripts/`
- **Auth**: Skills use `$ENV_VAR` references, never hardcoded secrets; env var names derived from security scheme names
- **Naming**: Kebab-case for skill/group names, snake_case for Python modules
- **Python**: 3.11+ required; extensive type hints with `from __future__ import annotations`
