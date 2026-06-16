
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
