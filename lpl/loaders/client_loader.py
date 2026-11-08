"""Load a Client from a JSON file.

The reference client is never hardcoded. Any client can be loaded by
providing a path to its JSON file. A second client can be loaded without
any source code changes.
"""

from __future__ import annotations

import json
from pathlib import Path

from lpl.models.client import Client


def load_client_from_json(path: str | Path) -> Client:
    """Load and validate a Client from a JSON file.

    Parameters
    ----------
    path : str or Path
        Path to a JSON file conforming to the Client schema.

    Returns
    -------
    Client
        A fully validated Client object.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    pydantic.ValidationError
        If the JSON does not conform to the Client schema.
    json.JSONDecodeError
        If the file is not valid JSON.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Client file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    return Client.model_validate(data)
