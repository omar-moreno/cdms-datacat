
def normalize_path(path: str) -> str:
    """
    Ensures that the given path starts with '/CDMS/' and is properly
    formatted.


    This function performs the following checks and modifications:
    1. If the path is empty, it returns '/CDMS' as the default.
    2. If the path does not start with '/', a '/' is prepended.
    3. If the path does not start with '/CDMS', '/CDMS' is prepended (removing
       any leading slashes before).
    4. If the path already starts with '/CDMS', it is returned unchanged,
       ensuring that there are no redundant prefixes.
    5. Trailing slashes are removed from the final path.

    Args:
        path (str): The path to be corrected. Can be either absolute or
                    relative.

    Returns:
        str: The corrected path, ensuring it starts with '/CDMS/' and has no
             trailing slashes.

    Example:
        >>> normalize_path("/CUTE/Raw/Run1")
        '/CDMS/CUTE/Raw/Run1'

        >> normalize_path("")
        '/CDMS'
    """

    # If the path is empty, return "/CDMS" as a default
    if not path:
        return "/CDMS"

    # Ensure the path starts with "/"
    if path[0] != "/":
        path = "/" + path

    # Check if the path starts with "/CDMS", otherwise add it
    if not path.startswith("/CDMS"):
        path = "/CDMS" + path.lstrip("/")

    # Remove the trailing slash and return the normalized path
    return path.rstrip("/")

def getFileFormat(filePath):
    return "".join(pathlib.Path(filePath).suffixes).strip(".")
