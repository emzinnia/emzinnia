#!/usr/bin/env python3
"""Main entry point for the GitHub Stats Card Generator."""

import argparse
import json
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from PIL import Image

from github_stats import GitHubStats
from pokemon import PokemonFetcher
from renderer import StatsCardRenderer


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a GitHub stats card image.",
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        help="Use cached GitHub stats instead of fetching from API (for faster dev iterations)",
    )
    return parser.parse_args()


def load_config(config_path: str | Path = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def main() -> int:
    """Generate the GitHub stats card."""
    args = parse_args()

    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    config_path = project_root / "config.yaml"
    output_path = project_root / "output" / "stats.png"
    env_path = project_root / ".env"
    cache_path = project_root / "output" / "stats_cache.json"

    # Load environment variables from .env file if it exists
    load_dotenv(env_path)

    print("=" * 50)
    print("GitHub Stats Card Generator")
    print("=" * 50)

    # Load configuration
    print("\n[1/4] Loading configuration...")
    try:
        config = load_config(config_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    github_username = config.get("github_username")
    if not github_username:
        print("Error: github_username not specified in config.yaml")
        return 1

    # Display name defaults to github username if not specified
    display_name = config.get("display_name", github_username)

    pokemon_team = config.get("pokemon_team", [])
    if len(pokemon_team) != 6:
        print(f"Warning: Expected 6 Pokemon, got {len(pokemon_team)}")

    theme = config.get("theme", {})
    excluded_languages = config.get("excluded_languages", [])
    blurb_lines = config.get("blurb", [])
    labels = config.get("labels", {})
    languages_config = config.get("languages", {})
    scale_language_bars = languages_config.get("scale_bars", True)
    language_gradient = languages_config.get("gradient", True)
    language_bar_border = languages_config.get("border", False)

    # Format team names for display (handle both string and dict formats)
    def format_pokemon_name(p):
        if isinstance(p, dict):
            name = p.get("name", "")
            return f"{name}✨" if p.get("shiny", False) else name
        return p

    print(f"  Username: {github_username}")
    print(f"  Pokemon Team: {', '.join(format_pokemon_name(p) for p in pokemon_team)}")

    # Fetch GitHub stats (or load from cache)
    print("\n[2/4] Fetching GitHub stats...")
    stats = None

    if args.cache and cache_path.exists():
        # Load stats from cache
        try:
            with open(cache_path, "r") as f:
                stats = json.load(f)
            print("  (Using cached stats)")
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Could not load cache ({e}), fetching fresh stats...")

    if stats is None:
        # Fetch fresh stats from GitHub API
        try:
            github = GitHubStats(github_username)
            stats = github.get_all_stats(excluded_languages=excluded_languages)
            # Save to cache for future use
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            print(f"Error fetching GitHub stats: {e}")
            return 1

    # Pass through config options so renderer can filter/style languages
    stats["excluded_languages"] = excluded_languages
    stats["scale_language_bars"] = scale_language_bars
    stats["language_gradient"] = language_gradient
    stats["language_bar_border"] = language_bar_border

    print(f"  Total stars: {stats['total_stars']:,}")
    print(f"  Total commits: {stats['total_commits']:,}")
    print(f"  Total PRs: {stats['total_prs']:,}")
    print(f"  Total issues: {stats['total_issues']:,}")
    print(f"  Contributions (last year): {stats['contributions']:,}")
    print(
        f"  Top languages: {', '.join(f'{lang} ({pct}%)' for lang, pct in stats['languages'])}"
    )

    # Fetch Pokemon sprites
    print("\n[3/4] Fetching Pokemon sprites...")
    pokemon_fetcher = PokemonFetcher()
    sprites = pokemon_fetcher.get_team_sprites(pokemon_team)
    fetched_count = sum(1 for s in sprites if s is not None)
    print(f"  Fetched {fetched_count}/{len(pokemon_team)} sprites")

    # Load profile image if it exists
    profile_image = None
    profile_path = script_dir / "assets" / "profile.png"
    if profile_path.exists():
        try:
            profile_image = Image.open(profile_path)
            print(f"  Loaded profile image: {profile_path}")
        except Exception as e:
            print(f"  Warning: Could not load profile image: {e}")

    # Render the card
    print("\n[4/4] Rendering stats card...")
    renderer = StatsCardRenderer(theme)
    renderer.render(
        sprites,
        stats,
        output_path,
        username=display_name,
        blurb_lines=blurb_lines,
        profile_image=profile_image,
        labels=labels,
    )

    print("\n" + "=" * 50)
    print(f"✓ Stats card generated successfully!")
    print(f"  Output: {output_path}")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())

