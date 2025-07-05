"""OMOP Lite - Get an OMOP CDM database running quickly."""

# Import CLI for convenience
try:
    from .cli import app, main_cli

    __all__ = ["app", "main_cli"]
except ImportError:
    __all__ = []
