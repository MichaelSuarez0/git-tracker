import asyncio
import logging
import os

from dotenv import load_dotenv

from git_tracker import GitHubCommitsTracker

# Configurar el root logger una vez
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] busc%(message)s"
)
logging.root.setLevel(logging.INFO)

load_dotenv()


TOKEN = os.getenv("GITHUB_API_TOKEN", "")
USERNAME = "MichaelSuarez0"
exclude = "palewire"


# Ejemplo de uso
async def main() -> None:
    tracker = GitHubCommitsTracker(TOKEN)
    commits = await tracker.get_commits_from_following(
        USERNAME, days=1, exclude=exclude
    )
    tracker.print_commits_report(commits)


if __name__ == "__main__":
    asyncio.run(main())
