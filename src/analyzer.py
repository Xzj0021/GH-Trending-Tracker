"""Trend analysis and categorization for GitHub repositories.

Provides:
- Categorization via keyword-based NLP (no heavy ML deps)
- Trend detection: new entries, rising stars, velocity tracking
- Optional OpenAI-powered Chinese summaries (if OPENAI_API_KEY is set)
- Historical comparison against previous scrapes stored in data/
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .crawler import RepoInfo

logger = logging.getLogger(__name__)

# ---- Category taxonomy (keyword → category) ----

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    (
        "AI / 大模型",
        [
            "llm", "gpt", "chatgpt", "transformer", "attention", "language model",
            "large language", "prompt", "rag", "retrieval augmented", "fine-tun",
            "finetun", "langchain", "llama", "mistral", "anthropic", "openai",
            "deep learning", "neural network", "diffusion", "stable diffusion",
            "text-to-image", "text to image", "generative", "copilot", "agent",
            "multi-agent", "multi agent", "hugging", "tokenizer", "embedding",
        ],
    ),
    (
        "机器学习 / 数据科学",
        [
            "machine learning", "ml ", " ml", "tensorflow", "pytorch", "jax",
            "scikit-learn", "sklearn", "xgboost", "lightgbm", "data science",
            "data mining", "pandas", "numpy", "jupyter", "computer vision",
            "nlp", "natural language", "reinforcement learning", "rl ",
            "classification", "regression", "clustering", "prediction",
            "onxx", "mlops", "feature engineering", "model training",
            "inference", "distillation", "quantization", "dataset",
        ],
    ),
    (
        "Web / 前端",
        [
            "react", "vue", "angular", "svelte", "next.js", "nextjs", "nuxt",
            "remix", "astro", "tailwind", "css", "html", "frontend", "front-end",
            "front end", "web component", "browser", "javascript framework",
            "typescript", "ui component", "ui library", "design system",
            "progressive web", "pwa", "ssr", "static site", "webassembly",
            "wasm", "htmx", "alpine", "jquery", "bootstrap",
        ],
    ),
    (
        "后端 / API",
        [
            "django", "flask", "fastapi", "express", "spring", "nestjs",
            "graphql", "rest api", "restful", "grpc", "microservice",
            "micro-service", "backend", "back-end", "back end", "server",
            "laravel", "rails", "gin", "echo", "fiber", "axum", "actix",
            "rocket", "middleware", "orm", "migration", "endpoint",
        ],
    ),
    (
        "DevOps / 基础设施",
        [
            "docker", "kubernetes", "k8s", "terraform", "ansible", "pulumi",
            "ci/cd", "ci cd", "ci-cd", "jenkins", "github actions", "gitlab ci",
            "devops", "infrastructure", "iac", "container", "orchestration",
            "helm", "prometheus", "grafana", "logging", "monitoring",
            "observability", "alerting", "sre", "platform engineering",
        ],
    ),
    (
        "数据库 / 存储",
        [
            "database", "sql", "nosql", "postgres", "mysql", "mariadb",
            "sqlite", "redis", "mongodb", "cassandra", "etcd", "tikv",
            "elasticsearch", "vector database", "time series", "graph database",
            "orm", "query", "cache", "storage", "data lake", "data warehouse",
            "lakehouse", "duckdb", "clickhouse", "s3", "minio",
        ],
    ),
    (
        "CLI / 工具",
        [
            "cli", "command-line", "command line", "terminal", "tui",
            "shell", "bash", "zsh", "powershell", "dotfiles", "tool",
            "utility", "productivity", "workflow", "automation",
            "package manager", "build tool", "bundler", "linter",
            "formatter", "dev tools", "developer tool",
        ],
    ),
    (
        "安全 / 隐私",
        [
            "security", "vulnerability", "exploit", "penetration", "firewall",
            "encryption", "cryptography", "ssl", "tls", "authentication",
            "authorization", "oauth", "jwt", "password", "privacy",
            "zero trust", "xss", "csrf", "sql injection", "cve",
            "threat", "malware", "antivirus", "audit", "compliance",
        ],
    ),
    (
        "区块链 / 加密货币",
        [
            "blockchain", "crypto", "bitcoin", "ethereum", "solana",
            "defi", "nft", "web3", "smart contract", "solidity",
            "consensus", "mining", "wallet", "dex", "token",
            "dao", "layer 2", "zk", "zero knowledge", "rollup",
        ],
    ),
    (
        "移动端",
        [
            "android", "ios", "swift", "kotlin", "flutter", "react native",
            "mobile", "app", "xamarin", "capacitor", "ionic",
            "wear os", "watchos", "tvOS", "mobile development",
        ],
    ),
    (
        "游戏开发",
        [
            "game", "unity", "unreal", "godot", "game engine",
            "rendering", "shader", "vulkan", "opengl", "directx",
            "game dev", "gamedev", "3d graphics", "animation",
            "physics engine",
        ],
    ),
    (
        "文档 / 知识管理",
        [
            "documentation", "wiki", "knowledge base", "note", "markdown",
            "obsidian", "logseq", "notion", "docs", "static site generator",
            "docusaurus", "mkdocs", "sphinx", "javadoc", "storybook",
            "blog", "cms", "content management",
        ],
    ),
]

# Flattened: keyword → category name
_KEYWORD_MAP: dict[str, str] = {}
for _cat, _keywords in CATEGORY_RULES:
    for kw in _keywords:
        _KEYWORD_MAP[kw] = _cat


def categorize(repo: RepoInfo) -> list[str]:
    """Return list of category names matching this repo.

    Checks repo description, name, and language against keyword taxonomy.
    """
    text = f"{repo.name} {repo.description} {repo.language}".lower()
    scores: dict[str, int] = defaultdict(int)

    for keyword, category in _KEYWORD_MAP.items():
        if keyword in text:
            scores[category] += 1

    # Sort by match count descending
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [cat for cat, _ in ranked[:3]]


# ---- Trend analysis ----

def load_history(data_dir: Path) -> dict[str, dict]:
    """Load previously saved trending data for historical comparison."""
    history: dict[str, dict] = {}
    for f in sorted(data_dir.glob("trending_*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                entries = json.load(fh)
                for entry in entries:
                    full_name = entry.get("full_name", "")
                    if full_name:
                        history[full_name] = entry
        except (json.JSONDecodeError, OSError):
            pass
    return history


def save_snapshot(repos: list[RepoInfo], data_dir: Path) -> None:
    """Save current trending data for future comparison."""
    data_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = data_dir / f"trending_{timestamp}.json"
    records = [{
        "full_name": r.full_name,
        "description": r.description,
        "language": r.language,
        "total_stars": r.total_stars,
        "stars_today": r.stars_today,
        "forks": r.forks,
        "url": r.url,
        "scraped_at": r.scraped_at,
    } for r in repos]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    logger.info("Saved snapshot: %s (%d repos)", path, len(records))

    # Keep only last 30 snapshots
    snapshots = sorted(data_dir.glob("trending_*.json"))
    for old in snapshots[:-30]:
        old.unlink()


def find_new_entries(repos: list[RepoInfo], history: dict[str, dict]) -> list[RepoInfo]:
    """Return repos that were NOT seen in any previous snapshot."""
    return [r for r in repos if r.full_name not in history]


def find_rising_stars(
    repos: list[RepoInfo],
    history: dict[str, dict],
    min_growth: int = 500,
) -> list[tuple[RepoInfo, int]]:
    """Return repos with significant star growth since last sighting.

    Growth = current total_stars - previous total_stars.
    """
    rising: list[tuple[RepoInfo, int]] = []
    for r in repos:
        prev = history.get(r.full_name)
        if prev and prev.get("total_stars", 0) > 0:
            growth = r.total_stars - prev["total_stars"]
            if growth >= min_growth:
                rising.append((r, growth))
    rising.sort(key=lambda x: -x[1])
    return rising


def compute_velocity(repos: list[RepoInfo]) -> list[RepoInfo]:
    """Sort repos by star velocity (stars_today, which is stars per day/week/month).

    Already sorted by stars_today descending — just return sorted copy.
    """
    return sorted(repos, key=lambda r: -r.stars_today)


def analyze(
    repos: list[RepoInfo],
    data_dir: Path,
    history: Optional[dict[str, dict]] = None,
) -> dict:
    """Run full analysis pipeline on trending repos.

    Returns a dict with all analysis results ready for report generation.
    """
    if history is None:
        history = load_history(data_dir)

    # Categorize all repos
    categorized: dict[str, list[RepoInfo]] = defaultdict(list)
    for r in repos:
        cats = categorize(r)
        for c in cats:
            categorized[c].append(r)
        if not cats:
            categorized["其他 / Uncategorized"].append(r)

    # Find new entries
    new_entries = find_new_entries(repos, history)

    # Find rising stars
    rising = find_rising_stars(repos, history)

    # Velocity ranking
    by_velocity = compute_velocity(repos)

    # Language distribution
    lang_dist: dict[str, int] = defaultdict(int)
    for r in repos:
        lang = r.language or "Unknown"
        lang_dist[lang] += 1

    # Save snapshot for next run
    save_snapshot(repos, data_dir)

    return {
        "total_repos": len(repos),
        "new_entries": new_entries,
        "rising_stars": rising,
        "by_velocity": by_velocity[:10],
        "categorized": dict(categorized),
        "language_distribution": dict(
            sorted(lang_dist.items(), key=lambda x: -x[1])
        ),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


# ---- Optional OpenAI integration ----

def summarize_with_ai(repos: list[RepoInfo]) -> Optional[str]:
    """Generate a Chinese summary of trending repos using OpenAI API.

    Requires OPENAI_API_KEY environment variable. Returns None if not configured.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        import openai  # type: ignore[import]
    except ImportError:
        logger.warning("openai package not installed, skipping AI summary")
        return None

    repo_list = "\n".join(
        f"- {r.full_name}: {r.description or '(no description)'}"
        for r in repos[:15]
    )

    prompt = (
        "以下是 GitHub Trending 上当前最热门的仓库列表。请用中文写一段简短的分析总结"
        "（200字以内），包括：当前技术热点、值得关注的新兴项目趋势。\n\n"
        f"{repo_list}"
    )

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning("OpenAI API call failed: %s", e)
        return None
