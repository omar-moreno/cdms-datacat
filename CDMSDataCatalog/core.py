
import configparser as cp
import logging

from datacat import client_from_config
from pathlib import Path
from importlib.resources import files

from .fetch import get_default_fetchdir

logger = logging.getLogger(__name__)

class CatalogCore:
    """
    """

    def __init__(self,
                 config_file_path: Optional[Path | str] = None,
                 default_fetchdir: Optional[Path | str] = None
                 ) -> None:
        """
        Initialize the CatalogCore instance.

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

    def ls(self, path: str ="/CDMS") -> Optional[List[str]]:
        """
        Return contents of a data catalog path.

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

        except NoSuchFileException as e:
            error_msg = f"Path does not exist: {path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg) from e

    def exist(self, path: str, version_id: Optional[str] = None, site: Optional[str] = None) -> bool:
        """
        Check if a dataset or path exists in the data catalog.

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
        if not path or path == "/": return False

        return self.client.exists(normalize_path(path), versionId, site)

    def rm(self, path: str, recursive: bool = False) -> None:
        """
        Remove an entry (dataset, group, or directory) from the data catalog.

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
            logger.critical(f"Safety Violation: Blocked recursive deletion of root path '/CDMS'")
            raise ValueError("Cannot recursively delete the root path '/CDMS'. This would destroy the entire catalog.")
        # ---------------------------------------------

        try:
            target = self.client.path(path)

            if isinstance(target, datacat.model.Dataset):
                # Case 1: It's a dataset
                self.client.rmds(path)
                logger.debug(f"Deleted dataset: {path}")
                return

            if not recursive:
                # Case 2: It's a container (Group/Folder) but not recursive
                if list(self.client.children(path)):
                    raise IOError(f"Cannot delete non-empty directory '{path}' without recursive=True")

                ctype = _determine_container_type(target)
                self.client.rmdir(path, type=ctype)
                logger.debug(f"Deleted {ctype}: {path}.")
                return

            # Case 3: Recursive deletion of a container
            # First, delete children
            children = list(self.client.children(path))
            
            for child in children:
                # Recursively call rm on children (always recursive for children)
                # We pass verbose=False for inner calls to avoid noise unless top-level is very verbose
                # Or we can keep verbose=True if they want full logs
                self.rm(child.path, recursive=True)
 
            # Finally, delete the container itself
            ctype = _determine_container_type(target_node)
            self.client.rmdir(path, type=ctype)
            logger.debug(f"Deleted {ctype} recursively: {path}")
            return

        except Exception as e:
            # Catch-all for unexpected client errors
            logger.exception(f"Unexpected error while deleting '{path}': {type(e).__name__}")
            raise IOError(f"Couldn't delete {path}: {e}") from e


    def _determine_container_type(node: object) -> str:
        """Helper to determine if a node is a 'group' or 'folder'."""
        if isinstance(node, datacat.model.Group):
            return "group"
        return "folder"
