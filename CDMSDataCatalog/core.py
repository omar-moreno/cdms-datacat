"""Core interface for interacting with the CDMS data catalog.

This module provides the [CatalogCore][CDMSDataCatalog.core.CatalogCore]
class, the foundational low-level API for browsing, querying and modifying
containers in the CDMS data catalog. It encapsulates configuration loading,
client initialization, and common catalog operations behind a simplified 
interface.

Higher-level components (datasets, groups, dependents, discovery) are built on
top of a single `CatalogCore` instance, which owns the authenticated client
connection and the shared low-level operations they all rely on.

The catalog connection is configured through a configuration file or
package-provided defaults. Authentication and connection settings are passed
directly to the underlying `datacat` client implementation.

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
expected to be rooted at `/CDMS` (see 
[`normalize_path`][CDMSDataCatalog.path_utils.normalize_path]). 
Destructive operations such as deletion include safeguards to prevent 
accidental removal of the catalog root.
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
    """Foundational interface for interacting with the CDMS data catalog.

    `CatalogCore` provides a low-level API for connecting to, browsing,
    querying, and modifying resources stored in the CDMS data catalog. It
    manages configuration loading, client initialization, path
    normalization, and common catalog operations such as creating directories,
    listing contents, checking existence, updating metadata and
    removing catalog entries.

    Parameters
    ----------
    config_file_path : pathlib.Path or str, optional
        Path to a configuration file containing catalog connection settings.
        The file must follow Python's `configparser` syntax, with all settings
        in a `[defaults]` section and at least a `url` key. If `None`, the
        package's bundled default configuration is used.
    default_fetchdir : pathlib.Path or str, optional
        Default local directory used for retrieving fetched datasets. 
        Resolution priority: (1) this argument, (2) the config file's 
        `default_fetchdir` setting, (3) a system default from 
        [`get_default_fetchdir`][CDMSDataCatalog.fetch.get_default_fetchdir].


    Raises
    ------
    FileNotFoundError
        If a specified config or the resolved fetch directory does not exist.
    ValueError
        If the configuration file is missing the `[defaults]` section or the 
        `url` key.

    Attributes
    ----------
    client : datacat.client.Client
        Initialized data catalog client used for all catalog operations.
    default_fetchdir : str
        Absolute path to the default local fetch directory.

    Notes
    -----
    All catalog paths are normalized before being passed to the underlying
    client. Most operations expect paths rooted at `/CDMS`. Destructive
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

    Recursively remove a directory and all of its contents:

    >>> catalog.rm("/CDMS/test", recursive=True)
    """

    def __init__(
        self,
        config_file_path: Path | str | None = None,
        default_fetchdir: Path | str | None = None,
    ) -> None:
        
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
        config = cp.ConfigParser()
        config.read(config_path)

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
        """List the contents of a catalog path.

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
            If `path` refers to a dataset rather than a directory.
        FileNotFoundError
            If `path` does not exist or cannot be accessed.

        Examples
        --------
        >>> core.ls("/CDMS/CUTE")
        ['/CDMS/CUTE/R10', '/CDMS/CUTE/R11', ...]
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

    def exists(
        self, path: str, version_id: str | None = None, site: str | None = None
    ) -> bool:
        """Check whether a dataset or path exists in the catalog.

        Queries the catalog to verify the existence of a resource at the given
        path, optionally narrowed by version and site. This performs a direct 
        lookup and does not raise for a missing resource; it returns `False`
        when the item is absent or the path is invalid. 

        This tests for the existence of a catalog *entry*, not a file on disk.

        Parameters
        ----------
        path : str
            The canonical path to check. Must best rooted at `/CDMS`. A path
            that is empty or exactly `/` is treated as invalid and returns 
            `False` without querying the backend.
        version_id : str, optional
            Specific version identifier to check against. If given, the check 
            is performed against this version rather than the latest. 
        site : str, optional
            Specific site (e.g. `"SLAC"`, `"SNOLAB"`) to check against. 

        Returns
        -------
        bool
            `True` if the resource exists at the specified path (and optional
            version/site), `False` otherwise.

        """
        # All data catalog paths need to start with "/CDMS"
        if not path or path == "/":
            return False

        return self.client.exists(normalize_path(path), version_id, site)

    def rm(self, path: str, recursive: bool = False) -> None:
        """Remove an entry (dataset, group, or directory) from the catalog.

        Parameters
        ----------
        path : str
            The full path of the entry to remove. Must be rooted at `/CDMS`.
        recursive : bool, default False
            If `True`, recursively deletes all contents within a directory
            before deleting the directory itself. If `False` and the path
            points to a non-empty container, an `OSError` is raised.
            Ignored when `path` refers to a dataset (the dataset is deleted 
            directly).

        Raises
        ------
        ValueError
            If a recursive deletion of the root path `/CDMS` is attempted. 
        OSError
            If deletion fails, including:

                - deleting a non-empty directory without `recursive=True`,
                - permission denied by catalog backend,
                - the path not found or otherwise inaccessible.

        Warning
        -------
        This is a destructive operation with no undo. Verify the target path
        before proceeding, especially when using `recursive=True`.

        Examples
        --------
        Remove a single dataset:

        >>> core.rm("/CDMS/test/example/data.mid.gz")

        Recursively remove a directory and everything beneath it:

        >>> core.rm("/CDMS/test", recursive=True)
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
            logger.exception(f"Unexpected error while deleting '{path}'")
            raise OSError(f"Couldn't delete {path}: {e}") from e

    def _determine_container_type(self, container: object) -> str:
        """Return the catalog container type for a specified container.

        Parameters
        ----------
        container : object
            A catalog object returned by the `datacat` client.

        Returns
        -------
        str
            `"group"` if the container is a group, otherwise `"folder"`.

        """
        if isinstance(container, Group):
            return "group"
        return "folder"

    def mkdir(
        self,
        path: str,
        parents: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Create a new directory in the catalog.

        Creates a directory at the given path, optionally creating any missing
        parents and attaching metadata. 

        Parameters
        ----------
        path : str
            Full path where the directory should be created. Must be rooted at
            `/CDMS`.
        parents : bool, default False
            If `True`, create any missing parent directories along the path
            (like `mkdir -p`). If `False` and a parent is missing, the backend 
            raises an error.
        metadata : dict of str, optional
            Metadata key-value pairs to associate with the new directory. All
            keys and values must be strings.

        Raises
        ------
        TypeError
            If `metadata` is not a dictionary or contains non-string keys
            or values.

        """
        path = normalize_path(path)
        logger.info(f"Creating directory: {path}")

        # Validate metadata if provided
        if metadata is not None:
            logger.debug(f"Metadata provided: {len(metadata)} key(s)")

            if not isinstance(metadata, dict):
                raise TypeError(
                    f"metadata must be a dict or None, got {type(metadata).__name__}"
                )

            for key, value in metadata.items():
                if not isinstance(key, str):
                    raise TypeError(
                        f"metadata keys must be strings, got {type(key).__name__}"
                    )

                if not isinstance(value, str):
                    raise TypeError(
                        f"metadata values must be strings, got {type(value).__name__}"
                    )

        self.client.mkdir(path, parents=parents, metadata=metadata)

    def add_metadata(
        self, path: str, metadata: dict[str, str], replace: bool = False
    ) -> bool:
        """Add or update metadata on a catalog container.

        Metadata is attached to catalog folders or groups as key-value pairs.
        If any of the provided keys already exist and `replace` is `False`,
        no changes are made and the method returns `False`.

        Parameters
        ----------
        path : str
            Path to the target folder or group.
        metadata : dict of str to str
            Metadata entries to add or update. All keys and values must be 
            strings.
        replace : bool, default False
            If `True`, existing entries may be overwritten. If any provided key
            already exists and `replace` is `False`, no changes are applied.

        Returns
        -------
        bool
            `True` if the metadata was successfully added or updated,
            `False` if the operation was skipped because one or more
            metadata keys already exist and `replace` is `False`.

        Raises
        ------
        TypeError
            If `metadata` is not a dictionary of string keys and values.
        FileNotFoundError
            If `path` does not exist.
        """
        # Normalize the group path
        path = normalize_path(path)
        logger.info(f"Attempting to add metadata to: {path}")

        # Validate metadata
        if not isinstance(metadata, dict):
            raise TypeError(f"metadata must be a dict, got {type(metadata).__name__}")

        for key, value in metadata.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"metadata keys must be strings, got {type(key).__name__}"
                )

            if not isinstance(value, str):
                raise TypeError(
                    f"metadata values must be strings, got {type(value).__name__}"
                )

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
