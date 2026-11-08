"""Client loaders — load Client objects from external data files.

No client data is hardcoded in source. All clients are loaded from files.
"""

from lpl.loaders.client_loader import load_client_from_json

__all__ = ["load_client_from_json"]
