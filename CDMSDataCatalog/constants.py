"""Shared constants for the CDMS DataCat package.

This module holds values that are referenced by multiple components and have no
behavior of their own. Keeping them here avoids duplication and prevents the
circular imports that would arise if these contants lived inside one of the 
functional modules that others depend on.
"""

from enum import Enum
from typing import Final

CDMS_ROOT: Final[str] = "/CDMS"
"""Root path for all CDMS catalog entries. Every catalog path is expected to
be rooted here (see [`normalize_path`][CDMSDataCatalog.path_utils.normalize_path])."""

DEFAULT_MAX_DATASETS: Final[int] = 1_000_000_000
"""Default upper bound on the number of datasets returned by group-retrieval
operations. Chosen to be effectively "all" without an unbounded request.
Used by [`Groups.retrieve_files`][CDMSDataCatalog.groups.Groups.retrieve_files]."""

class DepType(Enum):
    """Dependency relationship type between catalog containers.

    Used when adding or removing dependents to indicate the direction of the 
    relationship.

    Attributes
    ----------
    PREDECESSOR : str
        The dependent is an input/ancestor of the container (e.g. a dataset 
        that feeds into a group).
    SUCCESSOR : str
        The dependent is an output/descendant of the container (e.g. a group
        produced from a dataset).
    """

    PREDECESSOR = "predecessor"
    SUCCESSOR = "successor"
