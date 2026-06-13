import asyncio
import base64
import logging
import time
from typing import Any, Optional

import httpx


class GitHubRepositorySearch:
    def __init__(self, token: str) -> None:
        """
        Initialize the repository searcher with your GitHub token.

        Parameters
        ----------
        token : str
            GitHub Personal Access Token
        """
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.api_url = "https://api.github.com"
        self.search_url = f"{self.api_url}/search/repositories"
        self.code_search_url = f"{self.api_url}/search/code"

    def check_rate_limit(self, response: httpx.Response) -> tuple[int, int]:
        """
        Check the GitHub API rate limit status.

        Parameters
        ----------
        response : httpx.Response
            Response from GitHub API

        Returns
        -------
        tuple[int, int]
            Tuple with (remaining_requests, reset_time)
        """
        remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
        return remaining, reset_time

    async def search_repositories(
        self, query: str, page: int = 1, per_page: int = 100
    ) -> Optional[dict[str, Any]]:
        """
        Search for repositories on GitHub with automatic retry on rate limit.

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
        retries = 5

        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            for attempt in range(retries):
                try:
                    response = await client.get(self.search_url, params=params)
                    remaining, reset_time = self.check_rate_limit(response)
                    logging.info(f"API requests remaining: {remaining}")

                    if response.status_code == 429:
                        wait_time = max(int(reset_time - time.time()) + 1, 60)
                        logging.warning(
                            f"Rate limit exceeded. Waiting {wait_time} seconds..."
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    return response.json()

                except Exception as e:
                    logging.error(
                        f"Error querying GitHub API (attempt {attempt + 1}/{retries}): {e}"
                    )
                    if attempt < retries - 1:
                        wait_time = 2**attempt
                        logging.info(f"Retrying after {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        logging.error("Max retries reached. Skipping query.")
                        return None

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

        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            try:
                response = await client.get(self.code_search_url, params=params)
                remaining, reset_time = self.check_rate_limit(response)
                logging.info(f"Code search API requests remaining: {remaining}")

                if response.status_code == 403 and "rate limit" in response.text.lower():
                    wait_time = max(int(reset_time - time.time()) + 1, 60)
                    logging.warning(
                        f"Rate limit exceeded for code search. Waiting {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                    response = await client.get(self.code_search_url, params=params)

                response.raise_for_status()
                return response.json().get("total_count", 0) > 0

            except Exception as e:
                logging.error(f"Error searching code for {repo_full_name}: {e}")
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
        url = f"{self.api_url}/repos/{repo_full_name}/readme"

        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            try:
                response = await client.get(url)
                remaining, reset_time = self.check_rate_limit(response)
                logging.info(f"API requests remaining: {remaining}")

                if response.status_code == 429:
                    wait_time = max(int(reset_time - time.time()) + 1, 60)
                    logging.warning(
                        f"Rate limit exceeded for README. Waiting {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                    response = await client.get(url)

                if response.status_code == 404:
                    return ""  # No README found

                response.raise_for_status()
                content = base64.b64decode(response.json().get("content", "")).decode(
                    "utf-8", errors="ignore"
                )
                return content

            except Exception as e:
                logging.error(f"Error fetching README for {repo_full_name}: {e}")
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
        url = f"{self.api_url}/repos/{repo_full_name}/topics"
        headers = self.headers.copy()
        headers["Accept"] = "application/vnd.github.mercy-preview+json"

        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            try:
                response = await client.get(url)
                remaining, reset_time = self.check_rate_limit(response)
                logging.info(f"API requests remaining: {remaining}")

                if response.status_code == 429:
                    wait_time = max(int(reset_time - time.time()) + 1, 60)
                    logging.warning(
                        f"Rate limit exceeded for topics. Waiting {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                    response = await client.get(url)

                response.raise_for_status()
                return response.json().get("names", [])

            except Exception as e:
                logging.error(f"Error fetching topics for {repo_full_name}: {e}")
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
        url = f"{self.api_url}/repos/{repo_full_name}/languages"

        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            try:
                response = await client.get(url)
                remaining, reset_time = self.check_rate_limit(response)
                logging.info(f"API requests remaining: {remaining}")

                if response.status_code == 429:
                    wait_time = max(int(reset_time - time.time()) + 1, 60)
                    logging.warning(
                        f"Rate limit exceeded for languages. Waiting {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                    response = await client.get(url)

                response.raise_for_status()
                languages = response.json()
                return ", ".join(languages.keys()) if languages else "Unknown"

            except Exception as e:
                logging.error(f"Error fetching languages for {repo_full_name}: {e}")
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

        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            # First try as organization
            org_url = f"{self.api_url}/orgs/{owner}"
            try:
                response = await client.get(org_url)
                remaining, reset_time = self.check_rate_limit(response)
                logging.info(f"API requests remaining: {remaining}")

                if response.status_code == 429:
                    wait_time = max(int(reset_time - time.time()) + 1, 60)
                    logging.warning(
                        f"Rate limit exceeded for org details. Waiting {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                    response = await client.get(org_url)

                if response.status_code == 200:
                    org_data = response.json()
                    details["is_organization"] = True
                    details["followers"] = org_data.get("followers", 0)
                    details["location"] = org_data.get("location", "Unknown") or "Unknown"
                    details["email"] = org_data.get("email", "Unknown") or "Unknown"
                    details["twitter_username"] = (
                        org_data.get("twitter_username", "Unknown") or "Unknown"
                    )
                    details["repo_count"] = org_data.get("public_repos", 0)
                    logging.info(
                        f"Organization {owner} has {details['repo_count']} public repos, "
                        f"{details['followers']} followers"
                    )
                    return details

            except Exception as e:
                logging.error(f"Error checking organization {owner}: {e}")

            # If not org, try as user
            user_url = f"{self.api_url}/users/{owner}"
            try:
                response = await client.get(user_url)
                remaining, reset_time = self.check_rate_limit(response)
                logging.info(f"API requests remaining: {remaining}")

                if response.status_code == 429:
                    wait_time = max(int(reset_time - time.time()) + 1, 60)
                    logging.warning(
                        f"Rate limit exceeded for user details. Waiting {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                    response = await client.get(user_url)

                response.raise_for_status()
                user_data = response.json()
                details["followers"] = user_data.get("followers", 0)
                details["location"] = user_data.get("location", "Unknown") or "Unknown"
                details["email"] = user_data.get("email", "Unknown") or "Unknown"
                details["twitter_username"] = (
                    user_data.get("twitter_username", "Unknown") or "Unknown"
                )
                details["repo_count"] = user_data.get("public_repos", 0)
                logging.info(
                    f"User {owner} has {details['repo_count']} public repos, "
                    f"{details['followers']} followers"
                )
                return details

            except Exception as e:
                logging.error(f"Error fetching details for user {owner}: {e}")
                return details

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

        # Execute all requests concurrently
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

