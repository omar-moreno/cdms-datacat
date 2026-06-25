
from typing import Final

# The mandatory root prefix for all CDMS data catalog paths.
DEFAULT_PATH_PREFIX: Final[str] = "/CDMS"

# The maximum number of datasets that will be retrieved from the data catalog by 
# default.
DEFAULT_MAX_DATASETS: Final[int] = 1_000_000_000

class DepType(Enum):
    PREDECESSOR = "predecessor"
    SUCCESSOR = "successor"
