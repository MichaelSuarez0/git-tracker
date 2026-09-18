import asyncio
import logging

from conf import TOKEN, USERNAME
from dotenv import load_dotenv

from git_tracker import GitHubCommitsTracker

# Configurar el root logger una vez
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logging.root.setLevel(logging.INFO)

load_dotenv()

exclude = "MichaelSuarez0"


# Ejemplo de uso
async def main() -> None:
    tracker = GitHubCommitsTracker(TOKEN)
    commits = await tracker.get_commits_from_following(
        USERNAME, days=1, exclude=exclude
    )
    tracker.print_commits_report(commits)


if __name__ == "__main__":
    asyncio.run(main())
