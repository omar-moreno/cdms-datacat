"""
Utilities package for CDMS Data Catalog.
"""

# Import constants to make them available at the package level
from .constants import (
    DEFAULT_PATH_PREFIX,
)

# Import path utilities
from .path_utils import (
    normalize_path,
)

__all__ = [

    # Constants
    "DEFAULT_PATH_PREFIX",

    # path_utils
    "normalize_path",
]
