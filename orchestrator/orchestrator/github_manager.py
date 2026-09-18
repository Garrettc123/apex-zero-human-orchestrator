import structlog
from github import Github, GithubException
from tenacity import retry, stop_after_attempt, wait_exponential
from .config import settings
from .db import audit

log = structlog.get_logger()

class GitHubManager:
    def __init__(self):
        if not settings.github_token:
            log.warning("github_token_missing — repo creation will fail until set")
            self.client = None
        else:
            self.client = Github(settings.github_token)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def create_repo(self, name: str, description: str = "", private: bool = True) -> dict:
        if not self.client:
            raise RuntimeError("GitHub token not configured")
        
        org = self.client.get_organization(settings.github_org) if settings.github_org else self.client.get_user()
        
        try:
            repo = org.create_repo(
                name=name,
                description=description,
                private=private,
                auto_init=True,
                has_issues=True,
                has_projects=False,
                has_wiki=False
            )
            await audit("github_repo_created", resource_id=name, payload={"url": repo.html_url, "private": private})
            log.info("github_repo_created", name=name, url=repo.html_url)
            return {
                "full_name": repo.full_name,
                "html_url": repo.html_url,
                "clone_url": repo.clone_url,
                "private": repo.private
            }
        except GithubException as e:
            log.error("github_create_failed", name=name, error=str(e))
            raise

    async def push_scaffold(self, repo_full_name: str, files: dict[str, str]):
        """Push initial scaffolding files into the new repo."""
        if not self.client:
            raise RuntimeError("GitHub token not configured")
        repo = self.client.get_repo(repo_full_name)
        for path, content in files.items():
            try:
                repo.create_file(path, f"scaffold: {path}", content, branch="main")
            except GithubException as e:
                if e.status == 422:  # already exists
                    contents = repo.get_contents(path)
                    repo.update_file(path, f"update scaffold: {path}", content, contents.sha)
                else:
                    raise
        await audit("github_scaffold_pushed", resource_id=repo_full_name, payload={"files": list(files.keys())})
        log.info("scaffold_pushed", repo=repo_full_name, files=len(files))
