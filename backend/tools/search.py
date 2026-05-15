from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from tools.scraper import fetch_url

DDG_URL = "https://html.duckduckgo.com/html/?q={query}&kl=us-en"


async def search_web(query: str) -> list[dict]:
    """Search DuckDuckGo and return structured results."""
    url = DDG_URL.format(query=quote_plus(query))
    html = await fetch_url(url)
    return _parse_ddg_results(html)


def _parse_ddg_results(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for result in soup.select("div.result"):
        title_el = result.select_one("a.result__a")
        snippet_el = result.select_one("a.result__snippet")

        if not title_el:
            continue

        href = title_el.get("href", "")
        results.append({
            "title": title_el.get_text(strip=True),
            "url": href,
            "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
        })

    return results[:10]
