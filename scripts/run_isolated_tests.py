"""Explicit opt-in CLI. Never give the web service Docker daemon access."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

parser=argparse.ArgumentParser(description="Run Python tests in an unprivileged, offline, read-only container. Containers are not a perfect boundary against hostile native code.")
parser.add_argument("repository",type=Path)
parser.add_argument("--enable-untrusted-tests",action="store_true",required=True)
args=parser.parse_args()
root=args.repository.resolve(strict=True)
if not root.is_dir() or root==Path("/") or "," in str(root):
    parser.error("Choose a repository directory without commas.")
with tempfile.TemporaryDirectory(prefix="sentinel-tests-") as directory:
    snapshot=Path(directory)/"repository"
    snapshot.mkdir(mode=0o755)
    count=total=0
    # Build a bounded, readable copy. Never change source permissions or follow links.
    for source in root.rglob("*"):
        relative=source.relative_to(root)
        if any(part in {".git",".venv","node_modules","__pycache__"} for part in relative.parts):
            continue
        count+=1
        if count>5000 or source.is_symlink():
            sys.exit("Snapshot exceeds entry limits or contains a symbolic link.")
        target=snapshot/relative
        if source.is_dir():
            target.mkdir(parents=True,exist_ok=True)
        elif source.is_file():
            size=source.stat().st_size
            total+=size
            if size>2_000_000 or total>60_000_000:
                sys.exit("Test snapshot exceeds size limits.")
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
            target.chmod(0o755 if source.stat().st_mode&0o111 else 0o644)
        else:
            sys.exit("Special files are not accepted.")
    for base,dirs,files in os.walk(snapshot):
        Path(base).chmod(0o755)
    name="sentinel-test-"+uuid.uuid4().hex
    command=["docker","run","--name",name,"--rm","--network=none","--read-only","--cap-drop=ALL","--security-opt=no-new-privileges","--pids-limit=64","--memory=256m","--cpus=1","--user=65534:65534","--tmpfs=/tmp:rw,noexec,nosuid,size=64m","--env=PYTHONDONTWRITEBYTECODE=1","--env=PYTEST_DISABLE_PLUGIN_AUTOLOAD=1","--mount",f"type=bind,src={snapshot},dst=/repo,readonly","sentinel-test-sandbox:local"]
    try:
        result=subprocess.run(command,timeout=60)
        sys.exit(result.returncode)
    except subprocess.TimeoutExpired:
        subprocess.run(["docker","kill",name],capture_output=True,timeout=10)
        sys.exit("Isolated test timeout reached.")
