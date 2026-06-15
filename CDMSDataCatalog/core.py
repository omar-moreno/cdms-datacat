
import configparser as cp
import logging

from pathlib import Path
from importlib.resources import files

logger = logging.getLogger(__name__)

class CatalogCore:
    """
    """

    def __init__(self, config_file_path = None, default_fetchdir = None):
        """
        """

        # If a user doesn't specify a configuration path, use the locally 
        # defined config. If a file isn't found at a specified path, throw
        # an exception.
        if config_file_path is None:
            config_path = files("CDMSDataCatalog").joinpath("cfg/default.cfg"))
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
