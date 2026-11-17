"""Run with python -m experiments.renderer_advanced.run; never mixes engines."""

import argparse
import json
import platform
import sys
import time

from fabrica.visual_storyboard import VisualStoryboard

from .adapters import (
    CHROME,
    ENG,
    EXP,
    NODE,
    OUT,
    ROOT,
    execute,
    load_config,
    select_adapter,
    sha,
)


def source_hashes():
    paths = [
        *EXP.rglob("*.py"),
        *EXP.rglob("*.html"),
        EXP / "config.json",
        ROOT / "src/fabrica/visual_storyboard.py",
    ]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def run(name, repeat=2):
    adapter = select_adapter(name)
    storyboard = VisualStoryboard.model_validate_json(
        (EXP / "storyboard.json").read_text()
    )
    adapter.validate(storyboard)
    if repeat != 2:
        raise ValueError("Two repetitions required")
    for i in (1, 2):
        if (OUT / name / f"run-{i}").exists():
            raise FileExistsError("Prior results preserved; use a new output directory")
    project = OUT / name / "project"
    build_start = time.perf_counter()
    adapter.build(storyboard, project)
    build_seconds = time.perf_counter() - build_start
    frozen = source_hashes()
    compositions = {
        str(p.relative_to(project)): sha(p) for p in project.rglob("*") if p.is_file()
    }
    versions = {
        "node": execute([NODE, "--version"]).strip(),
        "browser": execute([CHROME, "--version"]).strip(),
        "ffmpeg": execute(["ffmpeg", "-version"]).splitlines()[0],
        "git_sha": execute(["git", "rev-parse", "HEAD"]).strip(),
        "python": sys.version,
        "os": platform.platform(),
    }
    for i in (1, 2):
        assert source_hashes() == frozen, "Sources changed between repetitions"
        assert execute(["git", "rev-parse", "HEAD"]).strip() == versions["git_sha"]
        assert compositions == {
            str(p.relative_to(project)): sha(p)
            for p in project.rglob("*")
            if p.is_file()
            and not any(x.startswith(".") for x in p.relative_to(project).parts)
        }, "Project changed"
        directory = OUT / name / f"run-{i}"
        directory.mkdir(parents=True)
        manifest = {
            "build_wall_seconds": build_seconds,
            "renderer": name,
            "run": i,
            "engine_version": load_config()["renderers"][name],
            **versions,
            "storyboard_sha256": sha(EXP / "storyboard.json"),
            "source_sha256": frozen,
            "composition_sha256": compositions,
            "lockfile_sha256": sha(ENG / name / "package-lock.json"),
            "engine_package_sha256": sha(
                ENG / name / "node_modules" / name / "package.json"
            ),
            "status": "RUNNING",
            "human_review": "pending",
            "cache": {
                "render_parts_reused": False,
                "os_cache_cleared": False,
                "diagnostics_before_run": i == 1,
                "note": "First run warmed by check; second also benefits from OS/browser file cache",
            },
        }
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
        try:
            if i == 1:
                manifest["diagnostics"] = adapter.diagnostics(project, directory)
            manifest.update(adapter.render(project, directory))
            manifest.update(adapter.collect_metrics(directory))
            manifest.update(adapter.inspect(directory, storyboard))
            manifest["status"] = "PASS"
        except Exception as error:
            manifest.update(status="FAILED", error=str(error))
            raise
        finally:
            (directory / "manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
            )
        print(name, i, manifest["status"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renderer", required=True)
    args = parser.parse_args()
    names = ["givemotion", "hyperframes"] if args.renderer == "all" else [args.renderer]
    # Both adapters validated before any native render begins.
    for name in names:
        select_adapter(name)
    for name in names:
        run(name)


if __name__ == "__main__":
    main()
