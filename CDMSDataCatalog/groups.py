"""Module used to manage group operations within the CDMS Data Catalog.

This module provides the :class`Groups` class, which manages group operations
within the CDMS Data Catalog. It handles the lifecycle of metadata groups,
including creation, state management (open/closed), and the association of
datasets (predecessors and successors) with specific groups.
"""

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
    """Manage group operations in the CDMS Data Catalog.

    This class provides methods to create, retrieve, modify and manage the state
    of groups within the CDMS Data Catalog. It handles dependencies between groups
    and datasets, including adding predecessors and successors. The class assumes
    a valid ``CatalogCore`` instance is provided during initialization.

    Parameters
    ----------
    dc : CatalogCore
        The core data catalog instance used to perform low-level client operations
        such as fetching groups, managing metadata, and handling dependencies. This
        instance should be properly configured and ready.

    Attributes
    ----------
    dc: CatalogCore
        Reference to the core data catalog instance for all subsequent
        operations. Stored as an instance attribute for access by all
        methods in this class.

    """

    def __init__(self, dc: CatalogCore) -> None:
        """Initialize the Groups manager with a data catalog core instance.

        This constructor sets up the `Groups` object to manage group operations
        within the CDMS Data Catalog. It requires an initialized `CatalogCore`
        instance that provides access to the underlying data catalog client.

        Parameters
        ----------
        dc : CatalogCore
            The core data catalog instance used to perform low-level client
            operations such as fetching groups, managing metadata, and handling
            dependencies. This instance should be properly configured and ready
            for use before passing it to `Groups`.

        Returns
        -------
        None

        Attributes
        ----------
        dc : CatalogCore
            Reference to the core data catalog instance for all subsequent
            operations. Stored as an instance attribute for access by all
            methods in this class.

        """
        self.dc = dc

    def create(
        self, path: str, parents: bool = False, metadata: dict[str, str] | None = None
    ) -> None:
        """Create a new group at the specified path.

        Initializes a new group with a default "State" of "Open". If additional
        metadata is provided, it is merged with the default state.

        Parameters
        ----------
        path : str
            Full path to the new group (e.g., "/CDMS/Facility/Run/Group").
        parents : bool, optional
            If True, create any missing higher-level groups automatically.
            Default is False.
        metadata : dict[str, str], optional
            Additional metadata key-value pairs to associate with the group.
            These will be merged with the initial "State": "Open" metadata.
            Default is None.

        Returns
        -------
        None

        Raises
        ------
        FileExistsError
            If a group already exists at the specified path.

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

    def get(self, path: str, site: str = "All") -> CDMSGroup:
        """Retrieve a fully populated CDMSGroup object.

        Converts a string path into a full `CDMSGroup` object by fetching
        details from the data catalog.

        Parameters
        ----------
        path : str
            Path to the group to retrieve
        site : str, optional
            Site filter (e.g. "SLAC", "SNOLAB"). Use "All" (default) to query
            all sites.

        Returns
        -------
        CDMSGroup
            A `CDMSGroup` object representing the requested group, containing
            metadata and relationship information.

        """
        path = normalize_path(path)
        rawgroup = self.client.path(path, site=site)
        return CDMSGroup.fromGroup(rawgroup)

    def add_files(self, path: str, file_paths: Iterable[str]) -> None:
        """Add one or more dataset files to an open group.

        Links existing datasets to the group as predecessors. The group must be
        in an "Open" state to accept new files. Files can be specified as direct
        data catalog paths ("/CDMS/...") or filesystem paths containing exactly
        one "/CDMS/" segment.

        Parameters
        ----------
        path : str
            Path to target group.
        file_paths : itereable of str
            A sequence of file paths to add. Each path may be:
            - A Data Catalog path starting with "/CDMS/"
            - A filesystem path containing exactly one "/CDMS/", which will be
              converted to a Data Catalog path.

        Returns
        -------
        None

        Raises
        ------
            Exception
                If the group is in a closed state or a file path doesn't contain
                exactly one "/CDMS".

        """
        # Normalize the group path before using it
        path = normalize_path(path)

        # Get the group associated with the given path.
        group = self.get(path)

        # Check that the group can be modified.
        if not self.group_is_open(group):
            logger.exception(f"The group {group.name} is closed and can't be modified.")
            raise Exception(
                f"Group '{path}' is in a 'Closed' state and cannot be modified."
            )

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
                    raise Exception(f"Unrecognized CDMS path format: {file_path}")
            except Exception:
                raise

        # Add all datasets to the group as predecessors
        self.addDependents(group, DepType.PREDECESSOR.value, dep_datasets=datasets)

        for dataset in datasets:
            self.addDependents(dataset, DepType.SUCCESSOR.value, dep_groups=[group])

    def remove_files(self, group_name: str, paths: list[str]) -> None:
        """Remove datasets from a specified group.

        Removes the relationship between the group and the listed datasets.
        Supports wildcards in paths via `resolve_datasets`.

        Parameters
        ----------
        group_name : str
            The full path to the group from which datasets will be removed.
        paths : list of str
            List of file paths corresponding to the datasets to remove.
            Paths can be on disk or in the data catalog and may include
            wildcards (e.g. "/CDMS/Test/data*.txt").

        Returns
        -------
        None

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

        except Exception:
            raise

    def retrieve_files(
        self, path: str, num_datasets: int = DEFAULT_MAX_DATASETS
    ) -> list[CDMSDataset]:
        """Retrieve CDMSDataset objects associated with a group.

        Fetches the list of datasets linked to the specified group as predecessors.
        Defaults to returning all datasets unless a limit is set.

        Parameters
        ----------
        path : str
            The path to the group whose datasets should be retrieved.
        num_datasets : int, optional
            The maximum number of datasets to return. Defaults to a very large
            value (1 billion), effectively returning all dependents.

        Returns
        -------
        list of CDMSDataset
            A list of `CDMSDataset` objects associated with the group.
            Returns an empty list if the group does not exist or retrieval fails.

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

    def close(self, path: str) -> None:
        """Close a metadata group at the specified path.

        Updates the group's metadata to set the "State" to "Closed", preventing
        further additions of files until reopened.

        Parameters
        ----------
        path : str
            The path to the group that should be closed.

        Returns
        -------
        None

        """
        # Normalize the group path before using it
        path = normalize_path(path)

        # Close the group
        self.add_metadata(path, {"State": "Closed"}, replace=True)

    def open(self, path: str) -> None:
        """Open a metadata group at the specified path.

        Updates the group's metadata to set the "State" to "Open", allowing
        new files to be added.

        Parameters
        ----------
        path : str
            The path to the group that should be opened.

        Returns
        -------
        None

        """
        # Normalize the group path before using it
        path = normalize_path(path)

        # Close the group
        self.add_metadata(path, {"State": "Open"}, replace=True)

    def group_is_open(self, group: CDMSGroup) -> bool:
        """Determine whether a metadata group is currently open.

        Inspects the group's metadata and returns ``True`` if the value
        associated with the ``"State"`` key is ``"Open"``. If the key is
        missing or has any other value, the method returns ``False``.

        Parameters
        ----------
        group : CDMSGroup
            The group whose open/closed state should be checked.

        Returns
        -------
        bool
            ``True`` if the group is marked as open, ``False`` otherwise.

        Notes
        -----
        A group's state is tracked via its ``"State"`` metadata field. Other
        methods (e.g. `open`, `close`) update this field accordingly.

        """
        # If the group is open, return true.
        return group.metadata["State"] == "Open"
