# openclaw-skillify

Turn any API surface into [OpenClaw](https://github.com/openclaw/openclaw)/[nanobot](https://github.com/HKUDS/nanobot) skills.

Skillify discovers API endpoints from various sources, groups them into logical skills, and generates well-structured skill directories that any OpenClaw-compatible agent can use immediately.

## Install

```bash
pip install openclaw-skillify
```

## Quick Start

### From an OpenAPI spec

```bash
skillify run https://petstore.swagger.io/v2/swagger.json -o ./skills/
```

This discovers all endpoints, groups them by tag, and generates a skill directory per group — ready to drop into your nanobot workspace.

### Step by step

```bash
# 1. Discover the API
skillify discover https://api.example.com/openapi.json -o spec.json

# 2. (Optional) Edit spec.json to adjust groupings

# 3. Preview what would be generated
skillify preview spec.json

# 4. Generate skills
skillify generate spec.json -o ./skills/

# 5. Install directly into nanobot
skillify generate spec.json --install
```

### As a Python library

```python
from skillify.discover import discover
from skillify.generate import generate

spec = await discover("https://api.example.com/openapi.json")
result = await generate(spec, output_dir="./skills")
```

## Supported Sources

| Source | Flag | AI needed? |
|--------|------|------------|
| OpenAPI 3.x / Swagger 2.0 | `--source-type openapi` | No |
| GraphQL endpoint or `.graphql` file | `--source-type graphql` | No |
| HTML / Markdown documentation | `--source-type html` | Yes |
| Python package (installed) | `--source-type python` | No |

Source type is auto-detected by default. Use `-t` / `--source-type` to override.

## CLI Reference

```
skillify discover <source>          Discover API, output spec JSON
  -o, --output <path>               Output file (default: ./skillify-spec.json)
  -t, --source-type <type>          auto | openapi | graphql | html | python
  -m, --model <model>               LLM model for AI-aided steps

skillify generate <spec.json>       Generate skills from spec
  -o, --output-dir <path>           Output directory (default: ./skills/)
  --preview                         Dry-run, show what would be generated
  --install                         Copy to ~/.nanobot/workspace/skills/
  -m, --model <model>               LLM model for generation

skillify preview <spec.json>        Alias for generate --preview

skillify run <source>               Discover + generate in one step
  -o, --output-dir <path>           Output directory (default: ./skills/)
  -t, --source-type <type>          Source type
  -m, --model <model>               LLM model
  --install                         Copy to nanobot workspace
```

## How It Works

```
Source (URL/file/package)
  → Discovery (parse spec or AI-extract endpoints)
  → AI Analyzer (group endpoints, generate descriptions)
  → Planner (decide skill structure)
  → Generator (write SKILL.md + references + scripts)
  → Valid OpenClaw skills
```

The intermediate representation (`spec.json`) is human-editable JSON. You can tweak endpoint groupings, rename skills, or remove endpoints between discovery and generation.

## Generated Skill Format

Each skill follows the [OpenClaw skill format](https://github.com/openclaw/openclaw):

```
api-name-resource/
├── SKILL.md              # Frontmatter + usage instructions
├── references/           # Full endpoint docs (for large APIs)
└── scripts/              # Auth helpers (for OAuth2)
```

- Skills use `$ENV_VAR` for API keys — secrets are never hardcoded
- Large APIs (>8 endpoints per group) use progressive disclosure via `references/`
- Generated skills pass nanobot's built-in skill validation

## LLM Configuration

AI-aided steps (HTML discovery, endpoint grouping, skill body generation) use [litellm](https://github.com/BerriAI/litellm). Configure via environment variables:

```bash
export ANTHROPIC_API_KEY=sk-...          # or OPENAI_API_KEY, etc.
export SKILLIFY_MODEL=anthropic/claude-sonnet-4-5  # optional, default
```

OpenAPI and GraphQL discovery are fully deterministic and don't require an LLM.

## As an OpenClaw Skill

Skillify is also packaged as an OpenClaw skill. Install it into your nanobot workspace:

```bash
cp -r skill/skillify ~/.nanobot/workspace/skills/
```

Then from within nanobot, you can say things like "turn the Notion API into skills" and the agent will use skillify to do it.

## Development

```bash
git clone https://github.com/autoscreen/openclaw-skillify.git
cd skillifycode
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE)
