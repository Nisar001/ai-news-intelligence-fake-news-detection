from __future__ import annotations

from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.exceptions import DomainError


def _is_private_host(hostname: str | None) -> bool:
    if not hostname:
        return True
    return hostname in {"localhost", "127.0.0.1", "0.0.0.0"}


async def fetch_article_from_url(url: str, timeout_seconds: int = 10) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise DomainError("INVALID_URL", "Only HTTP/HTTPS URLs are allowed", 422)
    if _is_private_host(parsed.hostname):
        raise DomainError("INVALID_URL", "Private/local addresses are not allowed", 422)

    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds) as client:
        resp = await client.get(url, headers={"User-Agent": "AINewsIntelBot/1.0"})
        if resp.status_code >= 400:
            raise DomainError("FETCH_FAILED", f"Unable to fetch URL. HTTP {resp.status_code}", 422)

    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    text = "\n".join([p for p in paragraphs if p])
    if not text:
        raise DomainError("EMPTY_ARTICLE", "Could not extract readable content", 422)

    return {"title": title, "text": text, "source_url": url}
