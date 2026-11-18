"""Application renderer selection. No installation and no fallback on import."""

from .runtime import RendererConfig, RendererUnavailable


def select_renderer(config=None):
    from .native import GivemotionRenderer, HyperFramesRenderer

    config = config or RendererConfig()
    types = {"givemotion": GivemotionRenderer, "hyperframes": HyperFramesRenderer}
    if config.renderer not in types:
        raise RendererUnavailable(
            "Legacy renderer must be selected explicitly in the pipeline"
        )
    return types[config.renderer](config)
