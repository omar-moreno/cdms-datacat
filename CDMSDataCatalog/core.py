"""Core interface for interacting with the CDMS data catalog.

This module provides the :class:`CatalogCore` class, which serves as the
primary high-level API for browsing, querying, and modifying containers in
the CDMS data catalog. It encapsulates configuration loading, client
initialization, path normalization, and common catalog operations behind
a simplified interface.

The catalog connection is configured through a configuration file or
package-provided defaults. Authentication and connection settings are
passed directly to the underlying ``datacat`` client implementation.

Features
--------
- Load catalog configuration from user-specified or bundled configuration files.
- Initialize authenticated connections to the CDMS data catalog.
- Browse catalog contents and verify resource existence.
- Create and remove catalog directories, groups and datasets.
- Add or update metadata associated with catalog containers.
- Manage default data fetch locations for locally retrieved datasets.

Notes
-----
All catalog paths are normalized before being sent to the backend and are
expected to be rooted at ``/CDMS``. Destructive operations such as deletion
include safeguards to prevent accidental removal of the catalog root.

Classes
-------
CatalogCore
    Main interface for interacting with the CDMS data catalog.

"""

import configparser as cp
import logging
from importlib.resources import files
from pathlib import Path

from datacat import client_from_config
from datacat.model import Dataset, Group

from .fetch import get_default_fetchdir
from .path_utils import normalize_path

logger = logging.getLogger(__name__)


class CatalogCore:
    """Primary interface for interacting with the CDMS data catalog.

    ``CatalogCore`` provides a high-level API for connecting to, browsing,
    querying, and modifying resources stored in the CDMS data catalog. The
    class manages configuration loading, client initialization, path
    normalization, and common catalog operations such as creating directories,
    listing contents, checking dataset existence, updating metadata, and
    removing catalog entries.

    Parameters
    ----------
    config_file_path : Path or str, optional
        Path to a configuration file containing catalog connection settings.
        If not provided, the package's default configuration is used.
    default_fetchdir : Path or str, optional
        Default local directory used for retrieving fetched datasets. If not
        specified, the value is determined from the configuration file or
        system defaults.

    Attributes
    ----------
    client : datacat.client.Client
        Initialized data catalog client used for all catalog operations.
    default_fetchdir : str
        Absolute path to the default local fetch directory.

    Notes
    -----
    All catalog paths are normalized before being passed to the underlying
    client. Most operations expect paths rooted at ``/CDMS``. Destructive
    operations, such as recursive deletion, include safeguards to prevent
    accidental removal of critical catalog resources.

    Examples
    --------
    Create a catalog connection using the default configuration:

    >>> catalog = CatalogCore()

    List the contents of a catalog directory:

    >>> catalog.ls("/CDMS")
    ['/CDMS/ANIMAL', '/CDMS/AuxiliaryData', '/CDMS/CUTE', ...]

    Check whether a resource exists:

    >>> catalog.exist("/CDMS/SNOLAB")
    True

    Create a directory with metadata:

    >>> catalog.mkdir(
    ...     "/CDMS/test/example",
    ...     parents=True,
    ...     metadata={"owner": "analysis", "status": "active"},
    ... )

    Add metadata to an existing container:

    >>> catalog.add_metadata(
    ...     "/CDMS/test/example",
    ...     {"description": "Example directory"},
    ... )

    Remove an empty directory:

    >>> catalog.rm("/CDMS/test/example")

    Recursively remove a directory and all of its contents:

    >>> catalog.rm("/CDMS/test", recursive=True)

    """

    def __init__(
        self,
        config_file_path: Path | str | None = None,
        default_fetchdir: Path | str | None = None,
    ) -> None:
        """Initialize the CatalogCore instance.

        Loads configuration from file or package defaults, validates required
        settings, instantiates the client, and determines the data fetch directory
        based on argument priority rules.

        Parameters
        ----------
        config_file_path : Path or str, optional
            Absolute or relative path to the configuration file. Must contain
            a [defaults] section with at least the 'url' key. If None, loads
            from the package's embedded default configuration file.

        default_fetchdir : Path or str, optional
            The root directory from where fetched data is retrieved. Priority order:
            1. This argument value
            2. Config file's 'default_fetchdir' setting
            3. System default from get_default_fetchdir()

        Returns
        -------
        None

        Raises
        ------
        FileNotFoundError
            If a specified config file does not exist, or if the specified
            fetch directory cannot be accessed or does not exist.
        ValueError
            If the configuration file is missing the required [defaults] section
            or if the 'url' key is not found within it.

        Notes
        -----
        The configuration file must follow Python's configparser syntax.
        All settings including url, auth_type, auth_key_id, auth_secret_key, and
        default_fetchdir should be placed in the [defaults] section.

        """
        # If a user doesn't specify a configuration path, use the locally
        # defined config. If a file isn't found at a specified path, throw
        # an exception.
        if config_file_path is None:
            config_path = files("CDMSDataCatalog").joinpath("cfg/default.cfg")
        else:
            config_path = Path(config_file_path).resolve()

            if not config_path.exists():
                logger.error(f"Configuration file not found: {config_path}")
                raise FileNotFoundError(f"Config file not found: {config_path}")

        # Load the config
        config = cp.ConfigParser().read([config_path])

        # All settings should be in the [defaults] section
        if "defaults" not in config.sections():
            logger.error("Config file missing [defaults] section.")
            raise ValueError("Configuration must contain [defaults] section.")

        # At the very least, the data catalog URL needs to be specified
        if "url" not in config["defaults"]:
            logger.error("Data catalog URL not found in configuration.")
            raise ValueError("Data catalog URL not found in configuration.")

        # Instantiate the client
        self.client = client_from_config(dict(config.items("defaults")))

        # Determine default_fetchdir with clear priority
        if default_fetchdir is not None:
            fetchdir_path = Path(default_fetchdir).resolve()
        elif "default_fetchdir" in config["defaults"]:
            fetchdir_path = Path(config["defaults"]["default_fetchdir"]).resolve()
        else:
            fetchdir_path = Path(get_default_fetchdir()).resolve()

        if not fetchdir_path.exists():
            logger.error(f"Cannot access fetch directory: {fetchdir_path}")
            raise FileNotFoundError(f"Cannot access fetch directory: {fetchdir_path}")

        self.default_fetchdir = str(fetchdir_path)

    def ls(self, path: str = "/CDMS") -> list[str] | None:
        """Return contents of a data catalog path.

        Parameters
        ----------
        path : str, default "/CDMS"
            The path to list contents from.

        Returns
        -------
        list of str or None
            A list of containers (directories or datasets) if successful.

        Raises
        ------
        TypeError
            If a path refers to a dataset instead of a container.
        FileNotFoundError
            If the specified path doesn't exist or can't be accessed.

        """
        path = normalize_path(path)

        try:
            return [child.path for child in self.client.children(path)]

        except TypeError as e:
            # When the path points to a dataset, self.client.children returns
            # a single DataSet object instead of a list. In this case, the
            # above list comprehension fails and raises a TypeError exception.
            error_msg = f"Cannot list path '{path}': it is a dataset, not a directory"
            logger.error(error_msg)
            raise TypeError(error_msg) from e

        except FileNotFoundError as e:
            error_msg = f"Path does not exist: {path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg) from e

    def exist(
        self, path: str, version_id: str | None = None, site: str | None = None
    ) -> bool:
        """Check if a dataset or path exists in the data catalog.

        Queries the data catalog to verify the existence of a specific resource
        at the given path, optionally filtered by version ID and site. This method
        performs a direct lookup without raising exceptions for missing resources;
        it returns ``False`` if the item is not found or the path is invalid.

        Parameters
        ----------
        path : str
            The canonical path to check. Must start with "/CDMS". Paths
            consisting only of whitespace or equal to "/" are considered
            invalid and return "False" without querying the data catalog.
        version_id : str, optional
            Specific version identifier to check. If provided, the check is
            performed against this specific version rather than the latest.
        site : str, optional
            Specific site (e.g. SLAC, SNOLAB) associated with a dataset.

        Returns
        -------
        bool
            ``True`` if the resource exists at the specified path (and optional
            version/site), ``False`` otherwise.

        """
        # All data catalog paths need to start with "/CDMS"
        if not path or path == "/":
            return False

        return self.client.exists(normalize_path(path), version_id, site)

    def rm(self, path: str, recursive: bool = False) -> None:
        """Remove an entry (dataset, group, or directory) from the data catalog.

        WARNING::
            This is a destructive operation. There is no "undo" functionality.
            Ensure you have verified the target path before proceeding.

        Parameters
        ----------
        path : str
            The full path of the entry to remove. Must start with ``/CDMS``.
        recursive : bool, default False
            If ``True``, recursively deletes all contents within a directory
            before deleting the directory itself. If ``False`` and the path
            points to a non-empty container, an ``IOError`` will be raised.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If an attempt is made to recursively delete the root path "/CDMS".
        IOError
            Raised when deletion fails due to expected reasons:
                - Attempting to delete a non-empty directory without ``recursive=True``
                - Permission denied by the catalog backend
                - Path not found or inaccessible

        """
        path = normalize_path(path)

        # --- SAFETY CHECK: Prevent deletion of root ---
        if recursive and path == "/CDMS":
            logger.critical(
                "Safety Violation: Blocked recursive deletion of root path '/CDMS'"
            )
            raise ValueError("Cannot recursively delete the root path '/CDMS'!!!")
        # ---------------------------------------------

        try:
            target = self.client.path(path)

            if isinstance(target, Dataset):
                # Case 1: It's a dataset
                self.client.rmds(path)
                logger.debug(f"Deleted dataset: {path}")
                return

            if not recursive:
                # Case 2: It's a container (Group/Folder) but not recursive
                if list(self.client.children(path)):
                    raise OSError(f"Deleting '{path}' requires recursive=True")

                ctype = self._determine_container_type(target)
                self.client.rmdir(path, type=ctype)
                logger.debug(f"Deleted {ctype}: {path}.")
                return

            # Case 3: Recursive deletion of a container
            # First, delete children
            children = list(self.client.children(path))

            for child in children:
                # Recursively call rm on children (always recursive for children)
                self.rm(child.path, recursive=True)

            # Finally, delete the container itself
            ctype = self._determine_container_type(target)
            self.client.rmdir(path, type=ctype)
            logger.debug(f"Deleted {ctype} recursively: {path}")
            return

        except Exception as e:
            # Catch-all for unexpected client errors
            logger.error(
                f"Unexpected error while deleting '{path}': {type(e).__name__}"
            )
            raise OSError(f"Couldn't delete {path}: {e}") from e

    def _determine_container_type(self, node: object) -> str:
        if isinstance(node, Group):
            return "group"
        return "folder"

    def mkdir(
        self,
        path: str,
        parents: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Create a new directory in the data catalog.

        Creates a directory at the specified path with optional parent directory
        creation and custom metadata. This method supports hierarchical paths and
        allows for associating metadata with the newly created directory.

        Parameters
        ----------
        path : str
            The full path were the directory should be created. Must start with
            "/CDMS".
        parents : bool, default False
            If "True", creates any missing parent directories along the path
            (similar to "mkdir -p" in Unix). If "False" and any parent
            directory is missing, an "IOError" will be raised.
        metadata : dict, optional
            A dictionary of key-value pairs to associate with the new directory.

        Returns
        -------
        None

        Raises
        ------
        TypeError
            If "metadata" is provided but not a dict.

        """
        path = normalize_path(path)
        logger.info(f"Creating directory: {path}")

        # Validate metadata if provided
        if metadata is not None:
            if not isinstance(metadata, dict):
                raise TypeError(
                    f"metadata must be a dict or None, got {type(metadata).__name__}"
                )

            if metadata:
                logger.debug(f"Metadata provided: {len(metadata)} key(s)")

        self.client.mkdir(path, parents=parents, metadata=metadata)

    def add_metadata(
        self, path: str, metadata: dict[str, str], replace: bool = False
    ) -> bool:
        """Add or updates metadata for the specified container (folder, group).

        Args:
            path (str): The path to the folder or group.
            metadata (dict): The metadata to add or update.
            replace (bool): Whether to replace existing metadata (default is False).

        Returns:
            bool: True if metadata was successfully added or updated, False otherwise.

        """
        # Normalize the group path
        path = normalize_path(path)
        logger.info(f"Attempting to add metadata to: {path}")

        # Retrieve the container (folder, group) to add metadata to
        container = self.client.path(path)
        container_metadata = container.metadata

        existing_entries = set(metadata.keys()) & set(container_metadata.keys())

        if existing_entries and not replace:
            logger.info(f"The following metadata already exists: {existing_entries}.")
            return False

        # Update the containers metadata with the new metadata
        container.metadata = metadata

        # Commit the changes
        self.client.patchdir(container.path, container)

        return True
