"""Download pinned experiment runtimes locally on Ubuntu x86_64, then npm ci."""

import hashlib
import json
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path

EXP = Path(__file__).resolve().parent
ENG = EXP / "engines"
LOCK = json.loads((EXP / "runtime-lock.json").read_text())
CACHE = EXP.parents[1] / "out/renderer_ab/setup"


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def download(item, name):
    path = CACHE / name
    if not path.exists():
        urllib.request.urlretrieve(item["url"], path)
    if digest(path) != item["sha256"]:
        raise ValueError(f"Checksum mismatch: {path}")
    return path


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    ENG.mkdir(parents=True, exist_ok=True)
    node = download(LOCK["node"], "node.tar.xz")
    with tarfile.open(node) as archive:
        archive.extractall(ENG, filter="data")
    chrome = download(LOCK["chrome"], "chrome.zip")
    target = ENG / "chrome157"
    with zipfile.ZipFile(chrome) as archive:
        archive.extractall(target)
    for p in target.rglob("*"):
        if p.name in ["chrome-headless-shell", "chrome_crashpad_handler"]:
            p.chmod(0o755)
    libs = ENG / "browser-libs"
    libs.mkdir(exist_ok=True)
    for item in LOCK["libraries"]:
        p = libs / item["filename"]
        if not p.exists():
            subprocess.run(
                ["apt-get", "download", f"{item['package']}={item['version']}"],
                cwd=libs,
                check=True,
            )
        if digest(p) != item["sha256"]:
            raise ValueError(f"Checksum mismatch: {p}")
        subprocess.run(["dpkg-deb", "-x", str(p), str(libs / "root")], check=True)
    nodebin = ENG / f"node-v{LOCK['node']['version']}-linux-x64/bin"
    safe = {
        "PATH": f"{nodebin}:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "npm_config_cache": str(CACHE / "npm"),
    }
    for name in ["hyperframes", "givemotion"]:
        subprocess.run(
            [
                str(nodebin / "npm"),
                "ci",
                "--userconfig",
                "/dev/null",
                "--globalconfig",
                "/dev/null",
            ],
            cwd=ENG / name,
            env=safe,
            check=True,
        )
    subprocess.run(
        [str(EXP.parents[1] / ".venv/bin/python"), "-m", "pip", "freeze"], check=True
    )


if __name__ == "__main__":
    main()
