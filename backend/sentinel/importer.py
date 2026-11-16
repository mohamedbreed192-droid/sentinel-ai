"""Bounded public GitHub snapshot importer. Never invokes Git hooks or repository code."""
import io
import re
import tarfile
from pathlib import Path, PurePosixPath
import httpx

URL = re.compile(r"https://github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9_.-]{1,100})(?:\.git)?/?$")
EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml", ".toml", ".ini", ".txt", ".md", ".cfg"}

class ImportFailure(ValueError):
    pass

def parse_url(url: str) -> tuple[str, str]:
    match = URL.fullmatch(url)
    if not match:
        raise ImportFailure("Use an HTTPS public github.com/owner/repository URL without query or fragment.")
    owner, repo = match.groups()
    repo = repo.removesuffix(".git")
    if repo in {".", ".."} or not repo:
        raise ImportFailure("Invalid repository name.")
    return owner, repo

def extract_snapshot(data: bytes, root: Path) -> None:
    total = 0
    count = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive:
                count += 1
                if count > 5000:
                    raise ImportFailure("Snapshot exceeds the 5,000-entry limit.")
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts:
                    raise ImportFailure("Unsafe archive path.")
                if len(path.parts) < 2:
                    if member.isdir():
                        continue
                    raise ImportFailure("Archive must have a root directory.")
                if member.issym() or member.islnk() or member.isdev():
                    raise ImportFailure("Archive links and devices are not accepted.")
                if not member.isfile():
                    continue
                total += member.size
                if total > 60_000_000 or member.size > 2_000_000:
                    raise ImportFailure("Snapshot exceeds extraction limits.")
                relative = Path(*path.parts[1:])
                if any(part in {"node_modules", ".git", ".venv", "vendor"} for part in relative.parts):
                    continue
                if relative.suffix not in EXTENSIONS and relative.name != "Dockerfile":
                    continue
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source:
                    target.write_bytes(source.read())
    except (tarfile.TarError, EOFError) as error:
        raise ImportFailure("Invalid repository archive.") from error

def import_public(url: str, root: Path) -> dict:
    owner, repo = parse_url(url)
    with httpx.Client(timeout=30, follow_redirects=False, headers={"Accept": "application/vnd.github+json", "User-Agent": "sentinel-ai"}) as client:
        response = client.get(f"https://api.github.com/repos/{owner}/{repo}")
        if response.status_code != 200:
            raise ImportFailure("Public repository unavailable or GitHub rate limit reached.")
        metadata = response.json()
        if metadata.get("private") is not False or metadata.get("full_name", "").lower() != f"{owner}/{repo}".lower():
            raise ImportFailure("Only the requested public repository may be imported; renamed repositories must use their current URL.")
        commit = client.get(f"https://api.github.com/repos/{owner}/{repo}/commits", params={"per_page": 1})
        if commit.status_code != 200 or not commit.json():
            raise ImportFailure("Cannot resolve repository commit.")
        sha = commit.json()[0]["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ImportFailure("Invalid commit identifier.")
        chunks = bytearray()
        with client.stream("GET", f"https://codeload.github.com/{owner}/{repo}/tar.gz/{sha}") as archive:
            if archive.status_code != 200:
                raise ImportFailure("Cannot download repository snapshot.")
            for chunk in archive.iter_bytes():
                chunks.extend(chunk)
                if len(chunks) > 20_000_000:
                    raise ImportFailure("Compressed snapshot exceeds 20 MB.")
        extract_snapshot(bytes(chunks), root)
    return {"name": metadata["full_name"], "url": url, "commit": sha, "description": "Public repository snapshot", "stars": metadata.get("stargazers_count", 0)}
