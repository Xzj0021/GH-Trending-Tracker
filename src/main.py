"""Entry point for GH-Trending-Tracker.

Usage:
    python -m src.main              # Default: daily trending, top 10 per language
    python -m src.main --weekly     # Weekly trending
    python -m src.main --monthly    # Monthly trending
    python -m src.main --all        # Fetch all major languages
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .crawler import fetch_trending, fetch_all_languages
from .analyzer import analyze, summarize_with_ai
from .reporter import generate_report

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GitHub Trending Tracker — scrape, analyze, report"
    )
    parser.add_argument(
        "--since", default="daily",
        choices=["daily", "weekly", "monthly"],
        help="Trending time window (default: daily)",
    )
    parser.add_argument(
        "--language", default="",
        help="Filter by language (default: all languages)",
    )
    parser.add_argument(
        "--all-languages", action="store_true",
        help="Fetch trending across all major languages",
    )
    parser.add_argument(
        "--max", type=int, default=25,
        help="Max repos per query (default: 25)",
    )
    parser.add_argument(
        "--output", default="GH-TRENDING-REPORT.md",
        help="Output report path (default: GH-TRENDING-REPORT.md)",
    )
    parser.add_argument(
        "--data-dir", default="./data",
        help="Data directory for historical snapshots (default: ./data)",
    )
    parser.add_argument(
        "--ai", action="store_true",
        help="Enable AI-powered summary (requires OPENAI_API_KEY)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Verbose logging",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)

    data_dir = Path(args.data_dir)

    logger.info("=== GH-Trending-Tracker ===")
    logger.info("Since: %s, Language: %s", args.since, args.language or "all")

    # Fetch
    if args.all_languages:
        repos = fetch_all_languages(since=args.since)
    else:
        repos = fetch_trending(
            since=args.since,
            language=args.language,
            max_repos=args.max,
        )

    if not repos:
        logger.error("No repos fetched — exiting")
        sys.exit(1)

    logger.info("Fetched %d repos", len(repos))

    # Analyze
    analysis = analyze(repos, data_dir)

    # AI summary (optional)
    if args.ai:
        logger.info("Generating AI summary...")
        ai_summary = summarize_with_ai(repos)
        if ai_summary:
            analysis["ai_summary"] = ai_summary
        else:
            logger.warning("AI summary not available (check OPENAI_API_KEY)")

    # Report
    report = generate_report(analysis, output_path=Path(args.output))
    logger.info("Report saved to %s (%d chars)", args.output, len(report))

    # Quick summary to stdout
    print(f"\n{'='*60}")
    print(f"GitHub Trending Report — {args.since}")
    print(f"{'='*60}")
    print(f"Total repos:      {analysis['total_repos']}")
    print(f"New entries:      {len(analysis['new_entries'])}")
    print(f"Rising stars:     {len(analysis['rising_stars'])}")
    print(f"Categories found: {len(analysis['categorized'])}")
    if analysis.get("ai_summary"):
        print(f"\n🤖 AI 分析:\n{analysis['ai_summary']}")
    print(f"\nFull report: {args.output}")


if __name__ == "__main__":
    main()
