import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from git_tracker.utils.async_api_wrapper import AsyncApiWrapper


class GitHubCommitsTracker(AsyncApiWrapper):
    BASE_URL = "https://api.github.com"
    GRAPHQL_URL = "https://api.github.com/graphql"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Inicializa el tracker con tu token de GitHub

        Args:
            api_key: Personal Access Token de GitHub
        """
        super().__init__(api_key, timeout, logger)
        self.api_key = api_key
        self.headers = {
            "Authorization": f"bearer {self.api_key}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }
        self._client: Optional[httpx.AsyncClient] = None

    async def get_following(
        self, username: str, exclude: Optional[list[str] | str] = None
    ) -> list[dict[str, Any]]:
        """
        Obtiene la lista de usuarios que sigues

        Args:
            username: Tu nombre de usuario de GitHub

        Returns:
            Lista de diccionarios con información de usuarios
        """
        following = []
        page = 1

        while True:
            endpoint = f"/users/{username}/following"
            response = await self._api_request(
                endpoint, params={"per_page": 100, "page": page}
            )

            data = response.json()
            if not data:
                break

            following.extend(data)
            page += 1
            await asyncio.sleep(0.1)

        if exclude:
            if isinstance(exclude, str):
                exclude = [exclude]

            exclude_set = set(exclude)

            following_clean = [
                user_data
                for user_data in following
                if user_data.get("login") not in exclude_set
            ]
        else:
            following_clean = following

        self.logger.info(f"✓ Encontrados {len(following_clean)} usuarios que sigues")
        self.logger.debug(
            "\n"
            + json.dumps(following_clean, indent=2, ensure_ascii=False, default=str)
        )
        return following_clean

    async def get_user_contributions(
        self, username: str, days: int = 7
    ) -> Optional[dict[str, Any]]:
        """
        Obtiene las contribuciones de un usuario (los cuadritos verdes)

        Args:
            username: Nombre de usuario de GitHub
            days: Número de días hacia atrás para buscar

        Returns:
            Información de contribuciones del usuario
        """
        from_date = (datetime.now() - timedelta(days=days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        to_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        query = """
        query($username: String!, $from: DateTime!, $to: DateTime!) {
          user(login: $username) {
            contributionsCollection(from: $from, to: $to) {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    contributionCount
                    date
                  }
                }
              }
              commitContributionsByRepository(maxRepositories: 100) {
                repository {
                  name
                  owner {
                    login
                  }
                  url
                }
                contributions(first: 100) {
                  nodes {
                    commitCount
                    occurredAt
                  }
                  totalCount
                }
              }
            }
          }
        }
        """

        variables = {"username": username, "from": from_date, "to": to_date}

        client = await self._get_client()
        try:
            response = await client.post(
                self.GRAPHQL_URL, json={"query": query, "variables": variables}
            )
            self.api_calls += 1
            self.logger.debug(f"Api calls: {self.api_calls}")

            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    self.logger.debug(f"GraphQL errors: {data['errors']}")
                    return None
                return (
                    data.get("data", {})
                    .get("user", {})
                    .get("contributionsCollection", {})
                )
        except httpx.RequestError as e:
            self.logger.error(f"Error: {e}")

        return None

    async def get_commits_from_following(
        self, username: str, days: int, exclude: Optional[list[str] | str] = None
    ) -> dict[str, dict[str, Any]]:
        """
        Obtiene todos los commits de tus seguidos en un periodo de tiempo

        Args:
            username: Tu nombre de usuario de GitHub
            days: Número de días hacia atrás para buscar commits

        Returns:
            Diccionario con información de commits por usuario
        """
        following = await self.get_following(username, exclude)
        commits_data = {}

        self.logger.info(f"Buscando commits de los últimos {days} días...\n")

        tasks = [
            self._process_user(user, i, len(following), days)
            for i, user in enumerate(following, 1)
        ]

        results = await asyncio.gather(*tasks)

        for result in results:
            if result:
                user_login, data = result
                commits_data[user_login] = data

        return commits_data

    async def _process_user(
        self, user: dict[str, Any], index: int, total: int, days: int
    ) -> tuple[str, dict[str, Any]] | None:
        """Helper interno para procesar un usuario"""
        user_login = user["login"]
        self.logger.debug(f"[{index}/{total}] Verificando {user_login}...")

        contributions = await self.get_user_contributions(user_login, days)

        if not contributions:
            self.logger.debug(f"✗ {user_login}: Sin acceso")
            return None

        total_contributions = contributions.get("contributionCalendar", {}).get(
            "totalContributions", 0
        )

        if total_contributions == 0:
            self.logger.debug(f"✗ {user_login}: Sin commits")
            return None

        commits_by_repo = contributions.get("commitContributionsByRepository", [])

        commits_info = []
        total_commits = 0

        for repo_contrib in commits_by_repo:
            repo = repo_contrib.get("repository", {})
            repo_name = f"{repo['owner']['login']}/{repo['name']}"
            repo_url = repo.get("url", "")

            contributions_nodes = repo_contrib.get("contributions", {})
            commit_count = contributions_nodes.get("totalCount", 0)
            total_commits += commit_count

            nodes = contributions_nodes.get("nodes", [])
            for node in nodes:
                commits_info.append(
                    {
                        "repo": repo_name,
                        "repo_url": repo_url,
                        "commit_count": node.get("commitCount", 0),
                        "date": node.get("occurredAt", ""),
                    }
                )

        if total_commits > 0:
            self.logger.debug(f"✓ {user_login}: {total_commits} commits")
            return (
                user_login,
                {
                    "profile_url": user["html_url"],
                    "total_contributions": total_contributions,
                    "commits": commits_info,
                    "total_commits": total_commits,
                },
            )

        self.logger.debug(f"✗ {user_login}: Sin commits")
        return None

    def print_commits_report(self, commits_data: dict[str, dict[str, Any]]) -> None:
        """
        Imprime un reporte legible de los commits encontrados

        Args:
            commits_data: Diccionario con información de commits
        """
        if not commits_data:
            print("\n❌ No se encontraron commits en el periodo especificado")
            return

        print("\n" + "=" * 80)
        print("REPORTE DE COMMITS")
        print("=" * 80)

        sorted_users = sorted(
            commits_data.items(), key=lambda x: x[1]["total_commits"], reverse=True
        )

        for username, data in sorted_users:
            print(
                f"\n👤 {username} - {data['total_commits']} commits ({data['total_contributions']} contribuciones totales)"
            )
            print(f"   {data['profile_url']}")
            print("   " + "-" * 76)

            repos_summary: dict[str, dict[str, Any]] = {}
            for commit in data["commits"]:
                repo = commit["repo"]
                if repo not in repos_summary:
                    repos_summary[repo] = {
                        "count": 0,
                        "url": commit["repo_url"],
                        "dates": [],
                    }
                repos_summary[repo]["count"] += commit["commit_count"]
                repos_summary[repo]["dates"].append(commit["date"])

            for repo, info in list(repos_summary.items())[:5]:
                print(f"   📦 {repo} - {info['count']} commits")
                print(f"      🔗 {info['url']}")
                if info["dates"]:
                    latest = max(info["dates"])
                    date = datetime.strptime(latest, "%Y-%m-%dT%H:%M:%SZ")
                    print(f"      🕐 Último commit: {date.strftime('%Y-%m-%d %H:%M')}")
                print()

            if len(repos_summary) > 5:
                print(f"   ... y {len(repos_summary) - 5} repositorios más\n")

        print("=" * 80)
        print(f"Total: {len(commits_data)} usuarios con commits")
        total_commits = sum(data["total_commits"] for data in commits_data.values())
        print(f"Total de commits: {total_commits}")
        print("=" * 80)
