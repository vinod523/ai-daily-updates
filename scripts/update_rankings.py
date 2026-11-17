"""Refresh a reproducible, topic-based ranking using GitHub's public API."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TOPICS = ("artificial-intelligence", "machine-learning", "deep-learning", "llm", "generative-ai", "ai-agents")


def fetch_repositories():
    repositories = {}
    for topic in TOPICS:
        query = urlencode({"q": f"topic:{topic} archived:false fork:false", "sort": "stars", "order": "desc", "per_page": 100})
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "ai-daily-updates"}
        if os.environ.get("GH_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['GH_TOKEN']}"
        with urlopen(Request(f"https://api.github.com/search/repositories?{query}", headers=headers), timeout=60) as response:
            payload = json.load(response)
        if payload.get("incomplete_results"):
            raise RuntimeError(f"Incomplete GitHub results for {topic}; keeping previous rankings")
        for repo in payload["items"]:
            repositories[repo["full_name"]] = {
                "name": repo["full_name"], "url": repo["html_url"],
                "stars": repo["stargazers_count"], "forks": repo["forks_count"],
                "size_kb": repo["size"], "language": repo["language"],
                "description": repo["description"], "pushed_at": repo["pushed_at"],
            }
    return sorted(repositories.values(), key=lambda repo: (-repo["stars"], repo["name"]))[:100]


def cell(value):
    return str(value or "—").replace("|", "&#124;").replace("\n", " ").replace("\r", " ").replace("<", "&lt;")


def render(snapshot, previous):
    old = {repo["name"]: repo["stars"] for repo in previous.get("repositories", [])}
    lines = [
        "# AI Daily Updates", "",
        "A daily ranking of popular public AI repositories, ordered by GitHub stars.", "",
        f"Last successful refresh: **{snapshot['updated_at']}**.", "",
        "## Ranking", "",
        "Star change compares with the previous successful daily snapshot. New entries show —.", "",
        "| Rank | Repository | Stars | Change | Forks | Size (MiB) | Language |",
        "| ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for rank, repo in enumerate(snapshot["repositories"], 1):
        delta = f"{repo['stars'] - old[repo['name']]:+,}" if repo["name"] in old else "—"
        lines.append(f"| {rank} | [{repo['name']}]({repo['url']}) | {repo['stars']:,} | {delta} | {repo['forks']:,} | {repo['size_kb'] / 1024:,.1f} | {cell(repo['language'])} |")
    lines += ["", "## Methodology", "",
        "Each run fetches the top 100 non-fork, non-archived repositories for each topic: " + ", ".join(f"`{topic}`" for topic in TOPICS) + ". It deduplicates the results and publishes the top 100 by stars, with repository name breaking ties.", "",
        "This measures popularity within those topic searches, not every AI project on GitHub. Topic labels are maintained by repository owners and can include courses, resource lists, and applications. Stars do not measure code volume or quality. Size is GitHub's reported repository storage converted from KiB to MiB, not source lines of code.", "",
        "## Automatic updates", "",
        "GitHub Actions runs daily around **09:00 Asia/Kolkata (03:30 UTC)**. Scheduled runs can be delayed by GitHub. Use **Actions → Update AI rankings → Run workflow** for a manual refresh. No paid API or personal token is needed: the workflow uses its built-in GitHub token.", "",
        "The workflow commits only when generated content changes. Failed API requests leave the previous published ranking intact. Public repositories may have scheduled workflows disabled after 60 days without repository activity; re-enable the workflow if needed.", "",
        "Latest machine-readable data: [data/latest.json](data/latest.json). Daily snapshots: [data/history/](data/history/). Same-day reruns replace that day's snapshot and keep the comparison against the preceding day.", "",
        "## Run locally", "", "Requires Python 3.11 or newer. An authenticated GitHub token raises API rate limits.", "", "```sh", "GH_TOKEN=$(gh auth token) python3 scripts/update_rankings.py", "python3 -m unittest discover -s tests", "```", ""]
    return "\n".join(lines)


def main():
    now = datetime.now(timezone.utc)
    day = now.date().isoformat()
    history = ROOT / "data" / "history"
    earlier = sorted(path for path in history.glob("*.json") if path.stem < day)
    previous = json.loads(earlier[-1].read_text()) if earlier else {}
    snapshot = {"updated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"), "ranking_metric": "stars", "topics": list(TOPICS), "repositories": fetch_repositories()}
    if not snapshot["repositories"]:
        raise RuntimeError("No repositories returned; keeping previous ranking")
    content = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
    readme = render(snapshot, previous)
    history.mkdir(parents=True, exist_ok=True)
    (history / f"{day}.json").write_text(content)
    (ROOT / "data" / "latest.json").write_text(content)
    (ROOT / "README.md").write_text(readme)


if __name__ == "__main__":
    main()
