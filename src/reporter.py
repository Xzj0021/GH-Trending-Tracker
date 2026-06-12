"""Markdown report generation for GitHub Trending analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .crawler import RepoInfo


def _repo_row(repo: RepoInfo, extra: str = "") -> str:
    """Render a single repo as a markdown table row."""
    desc = repo.description[:80] + "..." if len(repo.description) > 80 else repo.description
    lang = repo.language or "—"
    stars = f"{repo.total_stars:,}"
    today = f"+{repo.stars_today:,}"
    extra_col = f" | {extra}" if extra else ""
    return (
        f"| [{repo.full_name}]({repo.url}) "
        f"| {desc} "
        f"| {lang} "
        f"| {stars} "
        f"| {today}{extra_col} |"
    )


def generate_report(analysis: dict, output_path: Optional[Path] = None) -> str:
    """Generate a Markdown report from analysis results.

    Args:
        analysis: Dict from analyzer.analyze().
        output_path: If set, write the report to this file.

    Returns:
        The report as a string.
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M UTC")

    lines: list[str] = []

    # Header
    lines.append(f"# GitHub 热点追踪日报")
    lines.append(f"")
    lines.append(f"**日期**: {date_str} | **更新时间**: {time_str}")
    lines.append(f"**收录仓库**: {analysis['total_repos']} 个")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # ---- 1. Top 10 by velocity ----
    lines.append(f"## 今日最热 (Star 增长最快)")
    lines.append(f"")
    lines.append(f"| 仓库 | 描述 | 语言 | 总 Stars | 今日新增 |")
    lines.append(f"|------|------|------|----------|----------|")
    for repo in analysis["by_velocity"][:10]:
        lines.append(_repo_row(repo))
    lines.append(f"")

    # ---- 2. New entries ----
    if analysis["new_entries"]:
        lines.append(f"## 新上榜项目 ({len(analysis['new_entries'])} 个)")
        lines.append(f"")
        lines.append(f"| 仓库 | 描述 | 语言 | 总 Stars | 今日新增 |")
        lines.append(f"|------|------|------|----------|----------|")
        for repo in analysis["new_entries"][:15]:
            lines.append(_repo_row(repo))
        lines.append(f"")

    # ---- 3. Rising stars ----
    if analysis["rising_stars"]:
        lines.append(f"## 快速增长项目 (历史对比)")
        lines.append(f"")
        lines.append(f"| 仓库 | 描述 | 语言 | 总 Stars | 增长量 |")
        lines.append(f"|------|------|------|----------|--------|")
        for repo, growth in analysis["rising_stars"][:15]:
            lines.append(_repo_row(repo, extra=f"+{growth:,}"))
        lines.append(f"")

    # ---- 4. By category ----
    lines.append(f"## 分类浏览")
    lines.append(f"")
    categorized = analysis["categorized"]
    for category, repos in sorted(categorized.items(), key=lambda x: -len(x[1])):
        if not repos:
            continue
        lines.append(f"### {category} ({len(repos)} 个)")
        lines.append(f"")
        for r in repos[:8]:
            lines.append(f"- [{r.full_name}]({r.url}) — {r.description[:60] if r.description else '无描述'}")
        if len(repos) > 8:
            lines.append(f"- ... *还有 {len(repos) - 8} 个相关仓库*")
        lines.append(f"")

    # ---- 5. Language distribution ----
    lines.append(f"## 语言分布")
    lines.append(f"")
    lines.append(f"| 语言 | 数量 |")
    lines.append(f"|------|------|")
    for lang, count in analysis["language_distribution"]:
        lines.append(f"| {lang} | {count} |")
    lines.append(f"")

    # ---- 6. AI Summary (optional) ----
    ai_summary = analysis.get("ai_summary")
    if ai_summary:
        lines.append(f"## AI 趋势分析")
        lines.append(f"")
        lines.append(f"> {ai_summary}")
        lines.append(f"")

    # Footer
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"*本报告由 [GH-Trending-Tracker](https://github.com/Xzj0021/GH-Trending-Tracker) 自动生成*")

    report = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")

    return report
