import asyncio
import logging

from conf import TOKEN
from dotenv import load_dotenv

from git_tracker import GitHubRepositorySearch

load_dotenv()


# Example usage
async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    searcher = GitHubRepositorySearch(TOKEN)

    # Search for repositories
    print("Searching for ceplan repositories...")
    results = await searcher.search_repositories("ceplan language:python", page=1)

    if results and "items" in results:
        print(f"\n✓ Found {results['total_count']} repositories")
        print(f"Showing first {len(results['items'])} results:\n")

        for repo in results["items"][:3]:  # Only first 3
            repo_name = repo["full_name"]
            print(f"\n{'=' * 80}")
            print(f"📦 {repo_name}")
            print(f"⭐ {repo['stargazers_count']} stars")
            print(f"🔗 {repo['html_url']}")

            # Get full repo info
            info = await searcher.get_full_repo_info(repo_name)

            print(f"\n🏷️  Topics: {', '.join(info['topics']) or 'No topics'}")
            print(f"💻 Languages: {info['languages']}")

            owner = info["owner_details"]
            print(f"\n👤 Owner: {repo_name.split('/')[0]}")
            print(
                f"   {'🏢 Organization' if owner['is_organization'] else '👨‍💻 User'}"
            )
            print(f"   Followers: {owner['followers']}")
            print(f"   Location: {owner['location']}")
            print(f"   Public repos: {owner['repo_count']}")

            if info["readme"]:
                readme_preview = info["readme"][:200].replace("\n", " ")
                print(f"\n📄 README preview: {readme_preview}...")

            # Search for ceplan mentions in code
            has_ceplan = await searcher.search_code_in_repo(repo_name, "ceplan")
            print(
                f"\n🔍 'ceplan' mentions in code: {'✓ Yes' if has_ceplan else '✗ No'}"
            )


if __name__ == "__main__":
    asyncio.run(main())
