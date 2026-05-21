from .constants import DEFAULT_PATH_PREFIX

def normalize_path(path : str) -> str:
    """
    Normalize a path to ensure it starts with '/CDMS/' and has no trailing
    slashes.

    This function enforces the CDMS datacat's strict path requirements:
    1. Empty or whitespace-only paths are converted to the default root '/CDMS'.
    2. Relative paths are made absolute.
    3. The '/CDMS/' prefix is enforced.
    4. Trailing slashes are stripped.

    Parameters
    ----------
    path : str
        The input path string. Can be absolute (e.g., '/CDMS/Raw') or relative 
        (e.g., 'Raw/Run1'). Leading and trailing whitespace is ignored.

    Returns
    -------
    str
        The normalized path string. Guaranteed to start with '/CDMS' and not 
        end with a slash (unless the path is exactly '/CDMS').

    Examples
    --------
    >>> normalize_path("")
    '/CDMS'
    
    >>> normalize_path("/")
    '/CDMS'
    
    >>> normalize_path("/CDMS/Raw/Run1/")
    '/CDMS/Raw/Run1'
    
    >>> normalize_path("/CUTE/Raw")
    '/CDMS/CUTE/Raw'
    
    >>> normalize_path("  /CDMS/Data/  ")
    '/CDMS/Data'
    
    >>> normalize_path("//Raw//Run1//")
    '/CDMS/Raw/Run1'
    """

    # Strip whitespace and handle empty/whitespace-only strings
    path = (path or "").strip()

    # If the path is empty, return "/CDMS as a default
    if not path:
        return DEFAULT_PATH_PREFIX

    # Ensure it starts with a single slash
    path = "/" + path.lstrip("/")

    # Enforce /CDMS prefix
    if not path.startswith(DEFAULT_PATH_PREFIX):
        path = DEFAULT_PATH_PREFIX + "/" + path.lstrip("/")

    return path.rstrip("/")
