import asyncio

from conf import TOKEN, USERNAME

from git_tracker import GitHubCommitsTracker

OWNER = USERNAME
REPO = "ubigeos_peru"


# Ejemplo de uso
async def main() -> None:
    label = {"name": "P1", "description": "Prioridad alta", "color": "#e11d21"}
    tracker = GitHubCommitsTracker(TOKEN)
    await tracker.add_labels(OWNER, REPO, label)


if __name__ == "__main__":
    asyncio.run(main())
