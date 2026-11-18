"""Technical reinspection at the factory/publication boundary; no upload behavior."""

import json
import uuid
from pathlib import Path

from .renderers import select_renderer
from .renderers.native import AudioTrack
from .renderers.runtime import RendererConfig
from .visual_storyboard import VisualStoryboard


def inspect_job(job):
    job = Path(job).resolve()
    state = json.loads((job / "result.json").read_text())
    config = RendererConfig.model_validate(state["config"]["rendering"])
    board = VisualStoryboard.model_validate_json((job / "storyboard.json").read_text())
    manifest = state["config"].get("audio")
    audio = AudioTrack.model_validate(manifest) if manifest else None
    if audio:
        audio.verify()
    directory = job / "validation" / uuid.uuid4().hex
    directory.mkdir(parents=True)
    return select_renderer(config).inspect(job / "final.mp4", board, directory, audio)
