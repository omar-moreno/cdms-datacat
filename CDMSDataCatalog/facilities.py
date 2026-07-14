"""Facility lookup helpers for the CDMS Data Catalog.

This module provides small, stateless helper functions for working with CDMS
facility identifiers and fridge-run discovery. These helpers are shared by
higher-level components (dataset search construction and data-discovery
routines) and therefore live in their own module to avoid circular imports.

Functions
---------
facility_name
    Convert a numeric facility ID (the 2-digit series-name prefix) to its
    human-readable facility name.
last_fridge_run_number
    Determine the most recent fridge-run number for a given facility by
    inspecting the catalog.

Notes
-----
``last_fridge_run_number`` returns the sentinel value :data:`RUN_NOT_FOUND`
(``-999999``) on failure rather than raising, because existing callers rely on
this sentinel for control flow. Prefer checking against :data:`RUN_NOT_FOUND`
rather than hard-coding the literal.
"""

import logging

from .core import CatalogCore

logger = logging.getLogger(__name__)

#: Sentinel returned by :func:`last_fridge_run_number` when no run is found or
#: an error occurs. Callers should compare against this constant rather than
#: hard-coding the literal value.
RUN_NOT_FOUND: int = -999999

#: Mapping of numeric facility IDs (the leading 2 digits of a series name) to
#: their human-readable facility names.
FACILITIES: dict[int, str] = {
    1: "Soudan",
    2: "UCB",
    3: "CWRU",
    4: "UFL",
    5: "TAMU",
    6: "Queens",
    7: "UMN",
    8: "Denver",
    9: "SLAC",
    21: "TRIUMF",
    22: "FNAL",
    23: "CUTE",
    24: "SNOLAB",
    25: "NEXUS",
    26: "TUNL",
    51: "DMC",
    99: "DAQTesting",
}


def facility_name(facility_id: int) -> str:
    """Convert a numeric facility ID to its facility name.

    The facility ID is the 2-digit prefix of a CDMS series name.

    Parameters
    ----------
    facility_id : int
        The numeric facility identifier to look up.

    Returns
    -------
    str
        The corresponding facility name, or an empty string if the ID is not
        recognized.

    Examples
    --------
    >>> facility_name(23)
    'CUTE'
    >>> facility_name(9)
    'SLAC'
    >>> facility_name(999)
    ''
    """
    return FACILITIES.get(facility_id, "")


def last_fridge_run_number(dc: CatalogCore, facility: str = "CUTE") -> int:
    """Return the most recent fridge-run number for ``facility``.

    Inspects the children of ``/CDMS/<facility>`` and returns the largest
    integer run number found (run folders are named like ``"R14"``; the
    leading ``"R"`` is stripped before parsing). Folders whose names are not
    parseable as run numbers are ignored.

    Parameters
    ----------
    dc : CatalogCore
        Core catalog instance used to query the catalog.
    facility : str, default "CUTE"
        The facility whose runs should be inspected.

    Returns
    -------
    int
        The most recent fridge-run number, or :data:`RUN_NOT_FOUND`
        (``-999999``) if the path cannot be read or no run folders are found.

    Notes
    -----
    This function does not raise on failure; it returns :data:`RUN_NOT_FOUND`
    so that callers can branch on the sentinel. Prefer comparing against
    :data:`RUN_NOT_FOUND` rather than the literal.
    """
    base_path = "/CDMS/" + facility

    try:
        folder_list = dc.client.children(base_path)
    except Exception:
        logger.error('Unable to read datacatalog path "%s"', base_path)
        return RUN_NOT_FOUND

    if not folder_list:
        # NOTE: the original code referenced an undefined `datacat_path` here,
        # which would have raised a NameError. Use the correct `base_path`.
        logger.error("No fridge run found in %s", base_path)
        return RUN_NOT_FOUND

    last_run = RUN_NOT_FOUND
    for datacat_folder in folder_list:
        run = datacat_folder.name
        try:
            last_run = max(last_run, int(run[1:]))
        except ValueError:
            # Folder name isn't "R" + number; skip it.
            continue

    return last_run
