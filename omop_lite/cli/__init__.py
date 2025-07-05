"""OMOP Lite CLI module."""

from .main import app, main_cli

__all__ = ["app", "main_cli"]

# Make the module executable
if __name__ == "__main__":
    main_cli()
