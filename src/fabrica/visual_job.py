"""Visual stages within the main pipeline. Locks and script/catalog are owned by produce()."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from .render import subtitles
from .renderers import select_renderer
from .renderers.runtime import sha
from .visual_planner import plan_script, validate_correspondence
from .visual_storyboard import VisualStoryboard


def visual_stages(
    *,
    script,
    job,
    job_id,
    config,
    state,
    stage,
    save_state,
    storyboard_path=None,
    audio=None,
):
    def make_board():
        if storyboard_path:
            board = VisualStoryboard.model_validate_json(
                Path(storyboard_path).read_text()
            )
            if board.job_id not in (None, job_id):
                raise ValueError("Storyboard belongs to another job")
            board = board.model_copy(update={"job_id": job_id})
        else:
            board = plan_script(
                script,
                job_id,
                width=state["config"]["width"],
                height=state["config"]["height"],
                fps=config.fps,
                scene_seconds=config.scene_seconds,
            )
        if audio:
            board = board.model_copy(update={"audio": "external"})
        board = VisualStoryboard.model_validate(board.model_dump())
        validate_correspondence(script, board)
        save_state(job / "storyboard.json", board.model_dump(mode="json"))

    stage("STORYBOARD", [job / "storyboard.json"], make_board)
    board = VisualStoryboard.model_validate_json((job / "storyboard.json").read_text())
    validate_correspondence(script, board)
    if (board.width, board.height) != (
        state["config"]["width"],
        state["config"]["height"],
    ):
        raise ValueError("Storyboard resolution differs from job configuration")
    renderer = select_renderer(config)
    inputs = renderer.inputs(board, audio)
    signature = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    video, metrics, thumb = (
        job / "final.mp4",
        job / "render.json",
        job / "thumbnail.png",
    )
    packaged_stage = None
    # A publication package binds an immutable asset; never silently replace it on retry.
    if (job / "metadata.json").exists():
        package = json.loads((job / "metadata.json").read_text())
        if (
            not video.is_file()
            or sha(video) != package["asset_hash"]
            or state.get("render_inputs") != signature
        ):
            raise ValueError(
                "Packaged asset or render inputs changed; create a new job explicitly"
            )
        if not metrics.is_file() or not thumb.is_file():
            raise ValueError(
                "Packaged asset is missing its render receipt or thumbnail"
            )
        receipt = json.loads(metrics.read_text())
        if receipt.get("sha256") != sha(video) or receipt.get(
            "thumbnail_sha256"
        ) != sha(thumb):
            raise ValueError("Packaged render receipt or thumbnail changed")
        # Recover a lost stage marker only from immutable packaged artifacts.
        packaged_stage = {p.name: sha(p) for p in (video, metrics, thumb)}
    if state.get("render_inputs") != signature:
        state["stages"].pop("RENDER", None)
    anchors = job / "anchors.json"
    stage(
        "ANCHORS",
        [anchors],
        lambda: save_state(
            anchors,
            {
                "alignment": "planned; no phonetic synchronization",
                "segments": [a.model_dump() for s in board.scenes for a in s.anchors],
            },
        ),
    )
    srt = job / "subtitles.srt"
    durations = [s.end - s.start for s in board.scenes]
    stage(
        "SUBTITLES", [srt], lambda: subtitles(script.scenes, durations, srt, mock=False)
    )

    def render_action():
        attempts = job / "render"
        attempts.mkdir(exist_ok=True)
        directory = attempts / f"attempt-{uuid.uuid4().hex}"
        prepared = renderer.prepare(board, directory, audio)
        product = renderer.render(prepared, audio)
        # Only inspected complete native outputs become the public job artifacts.
        pending = job / f".final-{uuid.uuid4().hex}.partial.mp4"
        try:
            shutil.copyfile(product.video, pending)
            if sha(pending) != product.metrics["sha256"]:
                raise ValueError("Output hash changed during safe promotion")
            pending.replace(video)
        finally:
            pending.unlink(missing_ok=True)
        shutil.copyfile(product.thumbnail, thumb)
        save_state(
            metrics,
            product.metrics
            | {"quality": product.quality, "attempt_directory": str(directory)},
        )
        state["render_inputs"] = signature

    if packaged_stage is not None:
        # Auxiliary-stage repairs may invalidate downstream markers; restore only
        # after they complete, so an immutable packaged video is never re-rendered.
        state["stages"]["RENDER"] = packaged_stage
    stage("RENDER", [video, metrics, thumb], render_action)
    record = json.loads(metrics.read_text())
    if record["sha256"] != sha(video) or record["renderer"] != config.renderer:
        raise ValueError("Recorded renderer asset differs from result")
    state.update(
        renderer=config.renderer,
        render_metrics=record,
        quality=record["quality"],
        duration=board.duration,
        scene_durations=durations,
        audio_simulated=False,
        audio_present=audio is not None,
        narrative_anchors=str(anchors),
        storyboard=str(job / "storyboard.json"),
        thumbnail=str(thumb),
        publish_enabled=False,
        editorial_status="REQUIRES_REVIEW",
    )
