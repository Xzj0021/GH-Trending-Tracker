"""GitHub Trending page scraper.

Parses github.com/trending HTML and extracts structured repository data.
No official API exists for trending — we parse the server-rendered page.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://github.com/trending"
HEADERS = {
    "Accept": "text/html",
    "User-Agent": "GH-Trending-Tracker/1.0",
}


@dataclass
class RepoInfo:
    owner: str
    name: str
    full_name: str = field(init=False)
    description: str = ""
    language: str = ""
    total_stars: int = 0
    stars_today: int = 0
    forks: int = 0
    url: str = field(init=False)
    contributors: list[str] = field(default_factory=list)
    scraped_at: str = ""

    def __post_init__(self) -> None:
        self.full_name = f"{self.owner}/{self.name}"
        self.url = f"https://github.com/{self.full_name}"


def _parse_count(text: str) -> int:
    """Parse '1,234' or '1.2k' style star/fork counts into int."""
    text = text.strip().lower().replace(",", "")
    if text.endswith("k"):
        try:
            return int(float(text[:-1]) * 1000)
        except ValueError:
            return 0
    try:
        return int(text)
    except ValueError:
        return 0


def _extract_total_stars(article) -> int:
    """Find total star count from a trending article element."""
    for link in article.select("a"):
        href = link.get("href", "")
        text = link.get_text(strip=True)
        if "/stargazers" in href:
            return _parse_count(text)
    return 0


def _extract_forks(article) -> int:
    """Find fork count from a trending article element."""
    for link in article.select("a"):
        href = link.get("href", "")
        text = link.get_text(strip=True)
        if "/forks" in href:
            return _parse_count(text)
    return 0


def _extract_stars_today(article) -> int:
    """Find 'stars today' count from a trending article element."""
    for span in article.select("span.d-inline-block.float-sm-right"):
        text = span.get_text(strip=True)
        nums = re.findall(r"[\d,]+", text)
        if nums:
            return _parse_count(nums[0])
    # Fallback: look for any text containing 'stars today'
    for el in article.select("span"):
        text = el.get_text(strip=True)
        if "stars today" in text.lower() or "stars this week" in text.lower() or "stars this month" in text.lower():
            nums = re.findall(r"[\d,]+", text)
            if nums:
                return _parse_count(nums[0])
    return 0


def _extract_language(article) -> str:
    """Find programming language from a trending article element."""
    lang_el = article.select_one('[itemprop="programmingLanguage"]')
    if lang_el:
        return lang_el.get_text(strip=True)
    # Fallback: look for repo-language-color sibling
    color_el = article.select_one(".repo-language-color")
    if color_el and color_el.parent:
        return color_el.parent.get_text(strip=True)
    return ""


def _extract_contributors(article) -> list[str]:
    """Extract built-by contributor names."""
    contributors: list[str] = []
    for img in article.select('img[alt]'):
        alt = img.get("alt", "").strip()
        if alt.startswith("@") and len(alt) > 1:
            contributors.append(alt[1:])
    return contributors


def fetch_trending(
    since: str = "daily",
    language: str = "",
    max_repos: int = 50,
) -> list[RepoInfo]:
    """Fetch trending repositories from GitHub.

    Args:
        since: Time window — 'daily', 'weekly', or 'monthly'.
        language: Filter by programming language (empty = all languages).
        max_repos: Maximum number of repos to return (GitHub shows up to 25).

    Returns:
        List of RepoInfo dataclass instances.
    """
    url = BASE_URL
    if language:
        url += f"/{language.lower()}"
    url += f"?since={since}"

    logger.info("Fetching trending: %s", url)

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Failed to fetch trending page: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.select("article.Box-row")
    logger.info("Found %d repo articles on trending page", len(articles))

    repos: list[RepoInfo] = []
    scraped_at = datetime.now(timezone.utc).isoformat()

    for article in articles[:max_repos]:
        # Parse repo name from h2 > a
        h2 = article.select_one("h2")
        if not h2:
            continue
        name_link = h2.select_one("a")
        if not name_link:
            continue

        href = name_link.get("href", "").strip()
        # Normalize: remove trailing slash, split to owner/name
        href_clean = href.strip("/")
        parts = href_clean.split("/")
        if len(parts) < 2:
            continue
        owner, repo_name = parts[0], parts[1]

        # Description
        desc_el = article.select_one("p")
        description = desc_el.get_text(strip=True) if desc_el else ""

        # Language
        language_name = _extract_language(article)

        # Stats
        total_stars = _extract_total_stars(article)
        forks = _extract_forks(article)
        stars_today = _extract_stars_today(article)
        contributors = _extract_contributors(article)

        repo = RepoInfo(
            owner=owner,
            name=repo_name,
            description=description,
            language=language_name,
            total_stars=total_stars,
            stars_today=stars_today,
            forks=forks,
            contributors=contributors,
            scraped_at=scraped_at,
        )
        repos.append(repo)

    logger.info("Parsed %d repos from trending page", len(repos))
    return repos


def fetch_all_languages(
    since: str = "daily",
    languages: Optional[list[str]] = None,
    max_repos_per_lang: int = 10,
) -> list[RepoInfo]:
    """Fetch trending across multiple languages.

    Args:
        since: Time window.
        languages: List of languages to fetch. None = top 10 popular languages.
        max_repos_per_lang: Max repos per language.

    Returns:
        Combined list of RepoInfo, deduplicated by full_name.
    """
    if languages is None:
        languages = [
            "",  # all languages
            "python",
            "javascript",
            "typescript",
            "go",
            "rust",
            "java",
            "c++",
            "c",
            "c%23",  # C#
            "swift",
            "kotlin",
        ]

    seen: set[str] = set()
    all_repos: list[RepoInfo] = []

    for lang in languages:
        repos = fetch_trending(since=since, language=lang, max_repos=max_repos_per_lang)
        for r in repos:
            if r.full_name not in seen:
                seen.add(r.full_name)
                all_repos.append(r)

    logger.info("Total unique repos across %d languages: %d", len(languages), len(all_repos))
    return all_repos
