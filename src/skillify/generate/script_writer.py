from __future__ import annotations

from skillify.generate.planner import SkillPlan
from skillify.models import APISpec, AuthType


class ScriptWriter:
    """Generates helper scripts for skills."""

    def write(self, plan: SkillPlan, spec: APISpec) -> dict[str, str]:
        """Returns a dict of filename -> content for scripts/."""
        auth = plan.group.auth or spec.auth
        scripts = {}

        if auth.type == AuthType.OAUTH2:
            scripts["auth_setup.sh"] = self._oauth2_script(auth, spec)

        return scripts

    def _oauth2_script(self, auth, spec) -> str:
        env_var = auth.env_var or "OAUTH_TOKEN"
        return f"""#!/usr/bin/env bash
# OAuth2 authentication setup for {spec.api_name}
# This script helps obtain an OAuth2 token.

set -euo pipefail

if [ -n "${{${env_var}:-}}" ]; then
    echo "Token already set in ${env_var}"
    exit 0
fi

echo "OAuth2 setup for {spec.api_name}"
echo ""
echo "To authenticate, you need to:"
echo "1. Create an OAuth2 application in your {spec.api_name} settings"
echo "2. Obtain a client ID and client secret"
echo "3. Complete the OAuth2 flow to get an access token"
echo "4. Set the token: export {env_var}=your_token_here"
echo ""
echo "For more details, see the API documentation: {spec.base_url or 'N/A'}"
"""
