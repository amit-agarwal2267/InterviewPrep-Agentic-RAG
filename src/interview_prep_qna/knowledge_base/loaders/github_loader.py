import httpx

from interview_prep_qna.core.config import get_settings


def _headers(accept: str = "application/vnd.github+json") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {get_settings().github_token.get_secret_value()}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def list_accessible_repositories() -> list[dict]:
    """List every repository visible to the configured GitHub token."""
    repositories: list[dict] = []
    async with httpx.AsyncClient(timeout=30, headers=_headers()) as client:
        page = 1
        while True:
            response = await client.get(
                "https://api.github.com/user/repos",
                params={"per_page": 100, "page": page, "sort": "updated"},
            )
            response.raise_for_status()
            batch = response.json()
            repositories.extend(batch)
            if len(batch) < 100:
                break
            page += 1
    return repositories


async def list_repository_files(repository: dict) -> list[str]:
    """Return supported text/code files from a repository's complete Git tree."""
    settings = get_settings()
    extensions = tuple(
        extension.strip().lower()
        for extension in settings.github_sync_extensions.split(",")
        if extension.strip()
    )
    branch = repository.get("default_branch", "main")
    async with httpx.AsyncClient(timeout=30, headers=_headers()) as client:
        response = await client.get(
            f"https://api.github.com/repos/{repository['full_name']}/git/trees/{branch}",
            params={"recursive": "1"},
        )
    if response.status_code in {403, 404}:
        return []
    response.raise_for_status()
    payload = response.json()
    if payload.get("truncated"):
        raise RuntimeError(f"Git tree was truncated for {repository['full_name']}")
    return [
        item["path"]
        for item in payload.get("tree", [])
        if item.get("type") == "blob"
        and item["path"].lower().endswith(extensions)
        and item.get("size", 0) <= settings.github_max_file_bytes
    ]


async def fetch_changed_files(repo_full_name: str, paths: list[str]) -> dict[str, str]:
    results: dict[str, str] = {}
    async with httpx.AsyncClient(
        timeout=30, headers=_headers("application/vnd.github.raw+json")
    ) as client:
        for path in paths:
            resp = await client.get(
                f"https://api.github.com/repos/{repo_full_name}/contents/{path}",
            )
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            results[path] = resp.text
    return results
