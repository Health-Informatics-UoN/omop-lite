from omop_lite.cli import app, main_cli

# Re-export for backward compatibility
__all__ = ["app", "main_cli"]

if __name__ == "__main__":
    main_cli()
