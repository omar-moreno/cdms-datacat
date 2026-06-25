
import logging
from collections.abc import Iterable

from datacat.model import Dataset

from .CDMSDataset import CDMSDataset
from .CDMSGroup import CDMSGroup
from .contants import DEFAULT_MAX_DATASETS, DepType
from .core import CatalogCore
from .path_utils import normalize_path

logger = logging.getLogger(__name__)

class Groups:
    """
    Manage group operations in the CDMS Data Catalog.

    This class provides methods to create, retrieve, modify and manage the state
    of groups within the CDMS Data Catalog. It handles dependencies between groups
    and datasets, including adding predecessors and successors.

    Attributes
    ----------
    dc: CatalogCore
        The core data catalog instance used for operations.

    """
    def __init__(self, dc : CatalogCore) -> None:
        self.dc = dc

    def create(self, path: str, parents: bool = False,
               metadata: dict[str, str] | None = None) -> None:
        """Create a new group at the specified path.

        Args:
            path (str): Full path to the new group.
            parents (bool): If True, create any missing higher-level groups.
            metadata (dict, optional): Additional metadata to associate with
                the group.

        Returns:
            bool: True is the group was successfully created, False if it
                  already exists.

        """
        # Normalize the group path before using it
        path = normalize_path(path)

        # If additional metadata is passed, merge it with the initial "State"
        # metadata value. By default, a group will be in an "Open" state when
        # first created.
        init_metadata = {"State": "Open"}
        if metadata is not None:
            init_metadata = init_metadata | metadata

        # Attempt to create the group, handle the case where it already exists
        if not self.exist(path):
            self.client.mkgroup(path, parents=parents, metadata=init_metadata)
            logger.info(f"Group {path} has been created successfully.")
        else:
            logger.exception(f"WARNING: group {path} already exists")
            raise FileExistsError(f"Group {path} already exists")

    def get(self, path: str, site: str = "All"):
        """Convert a path (string) to a full CDMSGroup object"""
        path = normalize_path(path)
        rawgroup = self.client.path(path, site=site)
        return CDMSGroup.fromGroup(rawgroup)

    def add_files(self, path: str, file_paths: Iterable[str]) -> None:
        """Add one or more dataset files to an open group.

        Parameters
        ----------
        path : str Path to the group that should receive the files.
        file_paths : Iterable[str] A sequence of file paths. Paths may be:
            - A Data Catalog path starting with "/CDMS/"
            - A filesystem path containing exactly one "/CDMS/", which will be
              converted to a Data Catalog path.

        Returns
        -------
        bool
            True if all files were added successfully, False otherwise.

        """
        # Normalize the group path before using it
        path = normalize_path(path)

        # Get the group associated with the given path.
        group = self.get(path)

        # Check that the group can be modified.
        if not self.group_is_open(group):
            logger.exception(f"The group {group.name} is closed and can't be modified.")
            return False

        datasets = []
        for file_path in file_paths:
            try:
                # Case 1: Already a data catalog path
                if file_path.startswith("/CDMS/"):
                    datasets.append(self.get(file_path))
                # Case 2: A disk path containing exactly one "/CDMS/"
                elif file_path.count("/CDMS/") == 1:
                    _, subpath = file_path.split("/CDMS/", 1)
                    catalog_path = "/CDMS/" + subpath
                    datasets.append(self.get(catalog_path))
                else:
                    print(f"ERROR: unrecognized CDMS path format: {file_path}")
                    return False
            except Exception:
                print(f"ERROR: cannot find Data Catalog entry for file {file_path}")
                return False

        # Add all datasets to the group as predecessors
        self.addDependents(group, DepType.PREDECESSOR.value, dep_datasets=datasets)

        for dataset in datasets:
            self.addDependents(dataset, DepType.SUCCESSOR.value, dep_groups=[group])

        return True

    def remove_files(self, group_name: str, paths: list[str]) -> bool:
        """Removes datasets from the specified group in the CDMS Data Catalog.

        Parameters
        ----------
        group_name : (str)
            The name of the group from which datasets will be removed.
        paths : List[str]
            A list of file paths corresponding to the datasets that should be
            removed. The paths can either be paths on disk or data catalog paths.
            Both can include wildcards.

        Returns
        -------
        bool
            Returns `True` if the operation was successful, otherwise `False`.

        Examples
        --------
        >>> remove_files_from_group("/CDMS/Test/TestGroup", ["/CDMS/Scratch/TestBackground/test1*.txt"])

        """
        try:
            # Retrieve the group container that will be modified.
            group = self.getgroup(normalize_path(group_name))

            # Convert the list of paths to datasets.
            datasets: list[Dataset] = self.resolve_datasets(paths)

            # Remove the datasets from the groups.
            self.removeDependents(
                group, DepType.PREDECESSOR.value, dep_datasets=datasets
            )
            for dataset in datasets:
                self.removeDependents(
                    dataset, DepType.SUCCESSOR.value, dep_groups=[group]
                )

        except Exception as e:
            print(f"An error occurred: {e}")
            return False

        return True

    def retrieve_files(self, path: str, num_datasets: int = DEFAULT_MAX_DATASETS) -> list[CDMSDataset]:
        """Retrieve CDMSDataset objects associated with the given group.

        Parameters
        ----------
        path : str
            The path to the group whose datasets should be retrieved.
        num_datasets : int, optional
            The maximum number of datasets to return. Defaults to a very large
            value, effectively returning all dependents.

        Returns
        -------
        List[CDMSDataset]
            A list of CDMSDataset objects associated with the specified group.
            Returns an empty list if the group does not exist or retrieval fails

        """
        # Normalize the group path before using it
        path = normalize_path(path)

        try:
            # Get the group associated with the given path.
            group = self.getgroup(path)
        except Exception as e:
            print(f"ERROR: Could not retrieve group at path '{path}': {e}")
            return []

        try:
            # Retrieve dependents associated with this group
            return self.getDependents(group, "cdmsgroup", 1, num_datasets)
        except Exception as e:
            print(f"ERROR: Failed to retrieve datasets for group '{group.name}': {e}")
            return []

    def close(self, path: str):
        """Close a metadata group at the specified path.

        Parameters
        ----------
        path : str
            The path to the group that should be closed. The path will be
            normalized before being used.

        """
        # Normalize the group path before using it
        path = normalize_path(path)

        # Close the group
        self.add_metadata(path, {"State": "Closed"}, replace=True)

    def open(self, path: str):
        """Open a metadata group at the specified path.

        Parameters
        ----------
        path : str
            The path to the group that should be opened. The path will be
            normalized before being used.

        """
        # Normalize the group path before using it
        path = normalize_path(path)

        # Close the group
        self.add_metadata(path, {"State": "Open"}, replace=True)

    def group_is_open(self, group: CDMSGroup) -> bool:
        """Determine whether a metadata group is currently open.

        This method inspects the group's metadata and returns ``True`` if the
        value associated with the ``"State"`` key is ``"Open"``. If the key is
        missing or has any other value, the method returns ``False``.

        Parameters
        ----------
        group : CDMSGroup
            The group whose open/closed state should be checked.

        Returns
        -------
        bool ``True`` if the group is marked as open, ``False`` otherwise.

        Notes
        -----
        A group's state is tracked via its ``"State"`` metadata field. Other
        methods in this class (e.g., `open_group` or `close_group`) are expected
        to update this field accordingly

        """
        # If the group is open, return true.
        return group.metadata["State"] == "Open"

