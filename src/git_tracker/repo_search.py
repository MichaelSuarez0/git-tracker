import asyncio
import base64
import logging
from typing import Any, Optional

import httpx2

from git_tracker.utils.async_api_wrapper import AsyncApiWrapper


class GitHubRepositorySearch(AsyncApiWrapper):
    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize the repository searcher with your GitHub token.

        Parameters
        ----------
        api_key : str
            GitHub Personal Access Token
        """
        super().__init__(api_key, timeout, logger)
        self.api_key = api_key
        self.headers = {
            "Authorization": f"token {self.api_key}",
            "Accept": "application/vnd.github.v3+json",
        }
        self._client: Optional[httpx2.AsyncClient] = None

    async def search_repositories(
        self, query: str, page: int = 1, per_page: int = 100
    ) -> Optional[dict[str, Any]]:
        """
        Search for repositories on GitHub.

        Parameters
        ----------
        query : str
            Search query (e.g., "cardano language:python")
        page : int, optional
            Page number, by default 1
        per_page : int, optional
            Results per page (max 100), by default 100

        Returns
        -------
        dict[str, Any] or None
            Dictionary with search results or None if failed
        """
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
            "page": page,
        }
        try:
            response = await self.GET("/search/repositories", params=params)
            return response.json()
        except Exception as e:
            self.logger.error(f"Error querying GitHub API for repositories: {e}")
            return None

    async def search_code_in_repo(
        self, repo_full_name: str, search_term: str = "cardano"
    ) -> bool:
        """
        Search for a specific term in repository code.

        Parameters
        ----------
        repo_full_name : str
            Full repository name (e.g., "user/repo")
        search_term : str, optional
            Term to search in code, by default "cardano"

        Returns
        -------
        bool
            True if term is found, False otherwise
        """
        query = f"{search_term} repo:{repo_full_name}"
        params = {"q": query, "per_page": 1}
        try:
            response = await self.GET("/search/code", params=params)
            return response.json().get("total_count", 0) > 0
        except Exception as e:
            self.logger.error(f"Error searching code for {repo_full_name}: {e}")
            return False

    async def get_readme(self, repo_full_name: str) -> str:
        """
        Get the README content of a repository.

        Parameters
        ----------
        repo_full_name : str
            Full repository name (e.g., "user/repo")

        Returns
        -------
        str
            README content as plain text, or empty string if not found
        """
        endpoint = f"/repos/{repo_full_name}/readme"
        client = await self._get_client()
        try:
            response = await client.get(endpoint)
            if response.status_code == 404:
                return ""  # No README found
            response.raise_for_status()
            self.api_calls += 1
            content = base64.b64decode(response.json().get("content", "")).decode(
                "utf-8", errors="ignore"
            )
            return content
        except Exception as e:
            self.logger.error(f"Error fetching README for {repo_full_name}: {e}")
            return ""

    async def get_topics(self, repo_full_name: str) -> list[str]:
        """
        Get repository topics/tags.

        Parameters
        ----------
        repo_full_name : str
            Full repository name (e.g., "user/repo")

        Returns
        -------
        list[str]
            List of repository topics
        """
        endpoint = f"/repos/{repo_full_name}/topics"
        headers = self.headers.copy()
        headers["Accept"] = "application/vnd.github.mercy-preview+json"
        client = await self._get_client()
        try:
            response = await client.get(endpoint, headers=headers)
            response.raise_for_status()
            self.api_calls += 1
            return response.json().get("names", [])
        except Exception as e:
            self.logger.error(f"Error fetching topics for {repo_full_name}: {e}")
            return []

    async def get_repo_languages(self, repo_full_name: str) -> str:
        """
        Get programming languages used in a repository.

        Parameters
        ----------
        repo_full_name : str
            Full repository name (e.g., "user/repo")

        Returns
        -------
        str
            Comma-separated string of languages
        """
        endpoint = f"/repos/{repo_full_name}/languages"
        try:
            response = await self.GET(endpoint)
            languages = response.json()
            return ", ".join(languages.keys()) if languages else "Unknown"
        except Exception as e:
            self.logger.error(f"Error fetching languages for {repo_full_name}: {e}")
            return "Unknown"

    async def get_owner_details(self, owner: str) -> dict[str, Any]:
        """
        Get detailed information about a repository owner (user or organization).

        Parameters
        ----------
        owner : str
            Username or organization name

        Returns
        -------
        dict[str, Any]
            Dictionary with owner details (followers, location, email, etc.)
        """
        details = {
            "followers": 0,
            "location": "Unknown",
            "email": "Unknown",
            "twitter_username": "Unknown",
            "repo_count": 1,
            "is_organization": False,
        }
        client = await self._get_client()

        # First try as organization
        org_endpoint = f"/orgs/{owner}"
        try:
            response = await client.get(org_endpoint)
            if response.status_code == 200:
                self.api_calls += 1
                org_data = response.json()
                details["is_organization"] = True
                details["followers"] = org_data.get("followers", 0)
                details["location"] = org_data.get("location", "Unknown") or "Unknown"
                details["email"] = org_data.get("email", "Unknown") or "Unknown"
                details["twitter_username"] = (
                    org_data.get("twitter_username", "Unknown") or "Unknown"
                )
                details["repo_count"] = org_data.get("public_repos", 0)
                return details
        except Exception as e:
            self.logger.debug(f"Not an organization or error: {e}")

        # If not org, try as user
        user_endpoint = f"/users/{owner}"
        try:
            response = await client.get(user_endpoint)
            if response.status_code == 200:
                self.api_calls += 1
                user_data = response.json()
                details["followers"] = user_data.get("followers", 0)
                details["location"] = user_data.get("location", "Unknown") or "Unknown"
                details["email"] = user_data.get("email", "Unknown") or "Unknown"
                details["twitter_username"] = (
                    user_data.get("twitter_username", "Unknown") or "Unknown"
                )
                details["repo_count"] = user_data.get("public_repos", 0)
                return details
        except Exception as e:
            self.logger.error(f"Error fetching details for user {owner}: {e}")

        return details

    async def get_full_repo_info(self, repo_full_name: str) -> dict[str, Any]:
        """
        Get complete information about a repository.

        Fetches README, topics, languages, and owner details concurrently.

        Parameters
        ----------
        repo_full_name : str
            Full repository name (e.g., "user/repo")

        Returns
        -------
        dict[str, Any]
            Dictionary with all repository information
        """
        owner = repo_full_name.split("/")[0]

        readme_task = self.get_readme(repo_full_name)
        topics_task = self.get_topics(repo_full_name)
        languages_task = self.get_repo_languages(repo_full_name)
        owner_task = self.get_owner_details(owner)

        readme, topics, languages, owner_details = await asyncio.gather(
            readme_task, topics_task, languages_task, owner_task
        )

        return {
            "repo": repo_full_name,
            "readme": readme,
            "topics": topics,
            "languages": languages,
            "owner_details": owner_details,
        }
