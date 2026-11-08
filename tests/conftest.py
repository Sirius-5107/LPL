"""Shared pytest fixtures."""

from pathlib import Path
import pytest
from lpl.loaders.client_loader import load_client_from_json

REFERENCE_CLIENT_PATH = Path(__file__).parent.parent / "data" / "clients" / "reference_client.json"


@pytest.fixture
def reference_client():
    """Load the reference client from the JSON file."""
    return load_client_from_json(REFERENCE_CLIENT_PATH)
