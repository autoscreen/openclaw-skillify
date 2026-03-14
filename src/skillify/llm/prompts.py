"""Prompt templates for skillify's AI-aided steps."""

ENDPOINT_GROUPING_SYSTEM = """\
You are an API design expert. Group the given API endpoints into logical skill groups \
for an AI agent. Each group should map to a coherent capability (e.g., "issues", "users", "billing").

Rules:
- Group by resource/domain, not HTTP method.
- Each group should have 3-15 endpoints. Split larger groups.
- Group names: lowercase, hyphens, under 64 chars. Prefix with the API name if useful.
- Display names: human-readable title case.
- Description: write as an OpenClaw skill trigger — explain what the group does AND when an agent should use it.

Return JSON matching this schema exactly:
{
  "groups": [
    {
      "name": "api-name-resource",
      "display_name": "API Name Resource",
      "description": "Trigger-quality description...",
      "endpoint_indices": [0, 1, 2],
      "tags": ["resource"]
    }
  ]
}

endpoint_indices are zero-based indices into the endpoint list provided."""

ENDPOINT_GROUPING_USER = """\
API: {api_name}
Base URL: {base_url}

Endpoints:
{endpoints_text}

Group these endpoints into logical skills."""

DESCRIPTION_GENERATION_SYSTEM = """\
You are writing a skill description for an AI agent framework called OpenClaw/nanobot. \
The description is the PRIMARY trigger mechanism — the agent reads it to decide when to use the skill.

Rules:
- Include what the skill does AND specific triggers/contexts for when to use it.
- Be comprehensive but concise (1-3 sentences).
- Include action verbs and concrete use cases.
- Do NOT include markdown or special formatting.

Return JSON: {"description": "..."}"""

HTML_EXTRACTION_SYSTEM = """\
You are an API documentation expert. Extract API endpoints from the given documentation text.

For each endpoint found, extract:
- method (GET, POST, PUT, DELETE, PATCH)
- path (the URL path, using {param} for path parameters)
- summary (short one-line description)
- description (longer description if available)
- parameters (name, location, type, required, description)

Return JSON matching this schema:
{
  "api_name": "Name of the API",
  "base_url": "https://api.example.com",
  "auth": {
    "type": "bearer_token|api_key_header|api_key_query|basic_auth|oauth2|none",
    "env_var": "SUGGESTED_ENV_VAR_NAME",
    "header_name": "Authorization",
    "header_prefix": "Bearer",
    "description": "How to authenticate"
  },
  "endpoints": [
    {
      "method": "GET",
      "path": "/resource/{id}",
      "summary": "Get a resource by ID",
      "description": "",
      "parameters": [
        {"name": "id", "location": "path", "type": "string", "required": true, "description": "Resource ID"}
      ],
      "tags": ["resource"]
    }
  ]
}"""

AUTH_ANALYSIS_SYSTEM = """\
Analyze the API authentication pattern and suggest an environment variable name.

Return JSON:
{
  "type": "bearer_token|api_key_header|api_key_query|basic_auth|oauth2|none",
  "env_var": "SUGGESTED_ENV_VAR_NAME",
  "header_name": "Authorization",
  "header_prefix": "Bearer",
  "description": "Brief auth setup instructions"
}"""

SKILL_BODY_SYSTEM = """\
You are writing the markdown body of an OpenClaw/nanobot SKILL.md file. This will be read by an AI agent.

Rules:
- Start with an H1 heading matching the display name.
- Include a brief auth/setup section if auth is required.
- Show curl-based examples for key endpoints.
- Use $ENV_VAR for secrets, never hardcode values.
- Keep under 400 lines. For groups with >8 endpoints, only show the most important ones and reference the full list.
- Be concise — the agent is smart, only include non-obvious procedural knowledge.
- Use imperative/infinitive form.
- Do NOT create a "When to Use" section (that goes in frontmatter description).

Return the raw markdown body (no frontmatter, no fences)."""

EMOJI_SYSTEM = """\
Pick a single emoji that best represents this API or resource. Return JSON: {"emoji": "..."}"""
