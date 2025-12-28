"""GitHub API client for fetching user statistics."""

import os
from datetime import datetime
from typing import Any

import requests


class GitHubStats:
    """Fetches GitHub statistics for a user."""

    GRAPHQL_URL = "https://api.github.com/graphql"
    REST_API_URL = "https://api.github.com"

    def __init__(self, username: str, token: str | None = None):
        self.username = username
        self.token = token or os.environ.get("GITHUB_ACCESS_TOKEN")
        if not self.token:
            raise ValueError(
                "GitHub access token required. Set GITHUB_ACCESS_TOKEN environment variable."
            )
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def _fetch_repos(self, include_private: bool = False) -> list[dict[str, Any]]:
        """
        Fetch repositories for the user.

        If include_private is True, uses the authenticated `/user/repos` endpoint so
        private owner repos are included (token must belong to the user and have repo scope).
        """
        repos: list[dict[str, Any]] = []
        page = 1
        per_page = 100

        # `/user/repos` includes private repos for the authenticated user when type=owner.
        base_url = (
            f"{self.REST_API_URL}/user/repos"
            if include_private
            else f"{self.REST_API_URL}/users/{self.username}/repos"
        )

        while True:
            params = {
                "per_page": per_page,
                "page": page,
                "type": "owner",  # owner scope matches prior behavior
            }

            response = requests.get(base_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            page_repos = response.json()

            if not page_repos:
                break

            repos.extend(page_repos)

            if len(page_repos) < per_page:
                break

            page += 1

        return repos

    def get_commits_this_year(self) -> int:
        """Get the total number of commits for the current year using GraphQL."""
        current_year = datetime.now().year
        from_date = f"{current_year}-01-01T00:00:00Z"
        to_date = f"{current_year}-12-31T23:59:59Z"

        query = """
        query($username: String!, $from: DateTime!, $to: DateTime!) {
            user(login: $username) {
                contributionsCollection(from: $from, to: $to) {
                    totalCommitContributions
                    restrictedContributionsCount
                }
            }
        }
        """

        variables = {
            "username": self.username,
            "from": from_date,
            "to": to_date,
        }

        response = requests.post(
            self.GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            raise RuntimeError(f"GraphQL error: {data['errors']}")

        contributions = data["data"]["user"]["contributionsCollection"]
        total = contributions["totalCommitContributions"]
        restricted = contributions["restrictedContributionsCount"]

        return total + restricted

    def get_total_stars(self) -> int:
        """Get the total number of stars across all user repositories."""
        total_stars = 0
        repos = self._fetch_repos(include_private=True)

        for repo in repos:
            total_stars += repo.get("stargazers_count", 0)

        return total_stars

    def get_contribution_stats(self) -> dict[str, int]:
        """Get aggregated contribution stats for the user."""
        query = """
        query($username: String!) {
          user(login: $username) {
            contributionsCollection {
              totalCommitContributions
              restrictedContributionsCount
              contributionCalendar {
                totalContributions
              }
            }
            pullRequests {
              totalCount
            }
            issues {
              totalCount
            }
          }
        }
        """

        variables = {"username": self.username}

        response = requests.post(
            self.GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            raise RuntimeError(f"GraphQL error: {data['errors']}")

        user = data["data"]["user"]
        contributions = user["contributionsCollection"]

        total_commits = (
            contributions.get("totalCommitContributions", 0)
            + contributions.get("restrictedContributionsCount", 0)
        )

        return {
            "total_commits": total_commits,
            "total_prs": user.get("pullRequests", {}).get("totalCount", 0),
            "total_issues": user.get("issues", {}).get("totalCount", 0),
            "contributions": contributions.get("contributionCalendar", {}).get(
                "totalContributions", 0
            ),
        }

    def get_language_breakdown(self) -> dict[str, int]:
        """Get the breakdown of languages used across all repositories."""
        language_bytes: dict[str, int] = {}
        # First, get all repositories (including private owner repos)
        repos = self._fetch_repos(include_private=True)

        # Then, get language breakdown for each repository
        for repo in repos:
            if repo.get("fork"):
                continue  # Skip forked repositories

            repo_name = repo["name"]
            url = f"{self.REST_API_URL}/repos/{self.username}/{repo_name}/languages"

            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                repo_languages = response.json()
                for lang, bytes_count in repo_languages.items():
                    language_bytes[lang] = language_bytes.get(lang, 0) + bytes_count

        return language_bytes

    @staticmethod
    def _normalize_language_name(name: str) -> str:
        """Normalize a language name for case-insensitive comparison."""
        return (name or "").strip().casefold()

    def get_language_percentages(
        self, top_n: int = 5, excluded_languages: list[str] | None = None
    ) -> list[tuple[str, float]]:
        """Get the top N languages as percentages, optionally excluding some."""
        language_bytes = self.get_language_breakdown()

        if not language_bytes:
            return []

        # Remove excluded languages before selecting top N so we still return N items when possible.
        if excluded_languages:
            excluded = {
                self._normalize_language_name(x) for x in excluded_languages if x
            }
            if excluded:
                language_bytes = {
                    lang: bytes_count
                    for lang, bytes_count in language_bytes.items()
                    if self._normalize_language_name(lang) not in excluded
                }

        if not language_bytes:
            return []

        total_bytes = sum(language_bytes.values())

        # Sort by bytes and get top N
        sorted_languages = sorted(
            language_bytes.items(), key=lambda x: x[1], reverse=True
        )

        top_languages = sorted_languages[:top_n]

        # Calculate percentages
        result = []
        for lang, bytes_count in top_languages:
            percentage = (bytes_count / total_bytes) * 100
            result.append((lang, round(percentage, 1)))

        return result

    def get_all_stats(self, excluded_languages: list[str] | None = None) -> dict[str, Any]:
        """Get all statistics in a single call."""
        contribution_stats = self.get_contribution_stats()

        # Preserve existing key for backwards compatibility
        contribution_stats["commits_this_year"] = contribution_stats["total_commits"]

        return {
            **contribution_stats,
            "total_stars": self.get_total_stars(),
            "languages": self.get_language_percentages(excluded_languages=excluded_languages),
        }



