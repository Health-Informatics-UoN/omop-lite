"""Database-related CLI commands package."""

from .test import test_command
from .create_tables import create_tables_command
from .load_data import load_data_command
from .add_constraints import add_constraints_command
from .add_primary_keys import add_primary_keys_command
from .add_foreign_keys import add_foreign_keys_command
from .add_indices import add_indices_command
from .drop import drop_command

__all__ = [
    "test_command",
    "create_tables_command",
    "load_data_command",
    "add_constraints_command",
    "add_primary_keys_command",
    "add_foreign_keys_command",
    "add_indices_command",
    "drop_command",
]
