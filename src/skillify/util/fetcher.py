from __future__ import annotations

import httpx


async def fetch_url(url: str, timeout: float = 30.0) -> str:
    """Fetch content from a URL. Returns the response text."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


async def fetch_json(url: str, timeout: float = 30.0) -> dict:
    """Fetch JSON from a URL."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()
