"""Primary data catalog user interface.

This module provides [CDMSDataCatalog][CDMSDataCatalog.CDMSDataCatalog], 
the top-level facade that CDMS users interact with. It composes several focused 
sub-components (core catalog operations, dataset operations, group management, 
dependency handling, and data discovery) behind a single, stable public API.

The facade doesn't implement any logic but instead delegates to one of the 
composed sub-objects.  This keeps the public surface stable while the 
underlying implementation is free to evolve.

Architecture
------------

The facade wires the following components together in dependency order::

    CatalogCore (client + config + paths)
        │
        ├── Dependents  (dependency operations)
        ├── Datasets    (get/search/add/fetch; depends on paths + facilities)
        │       │
        │       └── used by ──┐
        ├── Groups      (group lifecycle; depends on Dependents + Datasets)
        └── Discovery   (CDMS-specific queries; depends on Datasets)

Notes
-----
All catalog paths are normalized (rooted as ``/CDMS``) before being sent to the
backend.  See :func:`.path_utils.normalize_path`.

Examples
--------
>>> dc = CDMSDataCatalog()
>>> dc.ls("/CDMS/CUTE")
['/CDMS/CUTE/R10', '/CDMS/CUTE/R11', ...]
>>> datasets = dc.findData(Facility="CUTE", nFridgeRun=14, ProdStep="BatNoise")
"""

import logging
from collections.abc import Iterable
from pathlib import Path

from . import facilities, paths
from .CDMSDataset import CDMSDataset
from .CDMSGroup import CDMSGroup
from .constants import DEFAULT_MAX_DATASETS
from .core import CatalogCore
from .datasets import Datasets
from .dependents import Dependents
from .discovery import Discovery
from .fetch import fetchdata
from .groups import Groups

__all__ = ["CDMSDataCatalog"]

log = logging.getLogger(__name__)


class CDMSDataCatalog:
    """Primary client for interacting with the CDMS data catalog.

    This is the main entry point for users. It provides a stable, 
    high-level API for browsing, searching, retrieving, registering and
    managing datasets and groups in the CDMS data catalog.

    The most commonly used methods are:

    - `ls` : list the contents of a directory.
    - `get`: retrieve a 
    [`CDMSDataset`][CDMSDataCatalog.CDMSDataset.CDMSDataset] by path.
    * `search`: search for datasets using query syntax
    * `fetch`: download datsets to local disk
    * `findData`: search using pre-defined CDMS keywords.


    Parameters
    ----------
    config_file_path : pathlib.Path or str, optional
        Path to a configuration file containing catalog connection settings.
        The file must follow Python's `configparser` syntax, with all settings
        in a `[defaults]` section and at least a `url` key. If `None`, the
        package's bundled default configuration is used.
    default_fetchdir : pathlib.Path or str, optional
        Default local directory for retrieving fetched datasets. Resolution
        priority: (1) this argument, (2) the config file's `default_fetchdir`
        setting, (3) a system default determined at runtime.
    
    Raises
    ------
    FileNotFoundError
        If a specified config file or the resolved fetch directory does not
        exist.
    ValueError
        If the configuration is missing the `[defaults]` section or the
        required `url` key.

    Attributes
    ----------
    client : datacat.client.Client
        The underlying data catalog client used for all backend operations.
    default_fetchdir : str
        Absolute path to the default local fetch directory.

    Notes
    -----
    Recognized configuration keys (all in the `[defaults]` section):

    - `url` : base URL for the catalog web interface (required).
    - `auth_type` : web authentication standard.
    - `auth_key_id` : authentication id.
    - `auth_secret_key` : authentication public key.
    - `default_fetchdir` : same as the `default_fetchdir` argument.

    """

    def __init__(
        self,
        config_file: Path | str | None= None,
        default_fetchdir: Path | str | None = None,
    ) -> None:

        self._core = CatalogCore(config_file, default_fetchdir)
        self.client = self._core.client
        self.default_fetchdir = self._core.default_fetchdir

        self._groups = Groups(self.client)
        self._datasets = Datasets(self.client)
        self._dependents = Dependents(self.client)

    
    # ==================================================================
    # Core catalog operations
    # ==================================================================
    def ls(self, path: str = "/CDMS") -> list[str] | None:
        """List the contents of a catalog directory.

        Parameters
        ----------
        path : str, default "/CDMS"
            The catalog path to list.

        Returns
        -------
        list of str or None
            The paths of the child containers (directories or datasets).

        Raises
        ------
        TypeError
            If `path` refers to a dataset rather than a directory.
        FileNotFoundError
            If `path` does not exist.

        Examples
        --------
        >>> dc.ls("/CDMS/CUTE")
        ['/CDMS/CUTE/R10', '/CDMS/CUTE/R11', ...]
        """
        self._core.ls(path)

    def exist(
        self, path: str, version_id: str | None = None, site: str | None = None
    ) -> bool:
        """Check whether a path exists in the catalog.

        Tests for the existence of a catalog *entry*, not a file on disk.

        Parameters
        ----------
        path : str
            The catalog path to check. Must be rooted at `/CDMS`.
        version_id : str, optional
            Specific version identifier to check against.
        site : str, optional
            Specific site (e.g. `"SLAC"`, `"SNOLAB"`) to check against.

        Returns
        -------
        bool
            `True` if the entry exists, `False` otherwise.
        """
        return self._core.exists(path, version_id, site)

    def rm(self, path: str, recursive: bool = False) -> None:
        """Remove an entry (dataset, group, or directory) from the catalog.

        Parameters
        ----------
        path : str
            The full catalog path to remove.
        recursive : bool, default False
            If `True`, recursively delete a directory's contents before deleting
            the directory itself. Ignored for datasets.

        Raises
        ------
        ValueError
            If a recursive deletion of the root path `/CDMS` is attempted.
        OSError
            If deletion fails (e.g. a non-empty directory without `recursive`).

        Warnings
        --------
        This is a destructive operation with no undo. Verify the target path
        before proceeding.
        """
        self._core.rm(path, recursive)

    def mkdir(
        self,
        path: str,
        parents: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Create a new directory in the catalog.

        Parameters
        ----------
        path : str
            Full path where the directory should be created.
        parents : bool, default False
            If `True`, create any missing parent directories (like `mkdir -p`).
        metadata : dict of str to str, optional
            Metadata key-value pairs to associate with the new directory.

        Raises
        ------
        TypeError
            If `metadata` is not a dict of string keys and values.
        """
        self._core.mkdir(path, parents, metadata)

    def add_metadata(
        self, path: str, metadata: dict[str, str], replace: bool = False
    ) -> bool:
        """Add or update metadata on a catalog container.

        Parameters
        ----------
        path : str
            Path to the target folder or group.
        metadata : dict of str to str
            Metadata entries to add or update.
        replace : bool, default False
            If `True`, existing entries may be overwritten. If any provided key
            already exists and `replace` is `False`, no changes are applied.

        Returns
        -------
        bool
            `True` if metadata was applied, `False` if skipped due to existing
            keys with `replace=False`.

        Raises
        ------
        TypeError
            If `metadata` is not a dict of string keys and values.
        FileNotFoundError
            If `path` does not exist.
        """
        return self._core.add_metadata(path, metadata, replace)

    # ==================================================================
    # Dataset operations
    # ==================================================================
    def get(self, path: str, site: str = "All") -> CDMSDataset:
        """Retrieve a fully populated dataset by path.

        Parameters
        ----------
        path : str
            Path to the dataset.
        site : str, default "All"
            Site filter (e.g. `"SLAC"`, `"SNOLAB"`). `"All"` queries every site.

        Returns
        -------
        CDMSDataset
            The dataset wrapper for the requested path.
        """
        return self._datasets.get(path, site)

    def search(self, path: str, site: str = "All", getallmetadata: bool = False, **kwargs) -> list[CDMSDataset]:
        """Search the catalog and return datasets sorted by path.

        See 
        [Search Syntax](https://github.com/slaclab/datacat/wiki/Search-Syntax) 
        for the nominal syntax for path wildcards and query operators.

        Search results do not include full metadata unless requested via the
        `show` keyword. If `getallmetadata` is `True`, each hit is re-fetched
        to attach its full metadata — this incurs a separate round trip per 
        dataset, so prefer `show` when possible.

        Parameters
        ----------
        path : str
            Full or partial path; may include wildcards.
        site : str, default "All"
            Restrict results to a site if given.
        getallmetadata : bool, default False
            If `True`, re-fetch each hit for full metadata.
        **kwargs
            Additional arguments forwarded to the client's search (e.g. `query`,
            `show`).

        Returns
        -------
        list of CDMSDataset
            Matching datasets, sorted by path.

        Examples
        --------
        Find all merged processed data for CUTE run 14:

        >>> dc.search('/CDMS/CUTE/R14/Processed/Releases/**',
        ...           query='nMergeLevel == 2')
        """
        return self._datasets.search(path, site, getallmetadata, kwargs)

    def add(self, ds: CDMSDataset, replace: bool = True, catch_errors: bool = True) -> None:
        """Register a new dataset entry in the catalog.

        Parameters
        ----------
        ds : CDMSDataset
            The dataset to add.
        replace : bool, default True
            If `True`, overwrite an existing entry at the same path.
        catch_errors : bool, default True
            If `False`, allow errors to propagate instead of being reported.
        """
        self._datasets.add(ds, replace, catch_errors)


    def addLoc(self, path: str, site: str, resource: str, catch_errors: str = True) -> None:
        """Add a new physical location to an existing registered dataset.

        Parameters
        ----------
        path : str
            Target dataset path in the catalog.
        site : str
            Site where the dataset physically resides (e.g. `"OSN"`, `"SLAC"`).
        resource : str
            The file resource path at the given site.
        catch_errors : bool, default True
            If `False`, allow errors to propagate.
        """
        self._datasets.add_loc(path, site, resource, catch_errors)

    def fetch(self, path: str, **kwargs) -> list[CDMSDataset]:
        """Download the dataset(s) at `path` to local disk.

        Only files not already present locally are downloaded. See
        [`fetchdata`][CDMSDataCatalog.fetch.fetchdata] for the accepted forms of
        `path` and the full set of keyword arguments.

        Parameters
        ----------
        path : str or CDMSDataset or list
            The file(s) to download. May be a catalog path, a wildcard query
            string, a [`CDMSDataset`][CDMSDataCatalog.CDMSDataset.CDMSDataset],
            or a list of these.
        **kwargs
            Additional arguments forwarded to
            [`fetchdata`][CDMSDataCatalog.fetch.fetchdata] (e.g. `dest`,
            `destRelative`, `maxthreads`, `force`).

        Returns
        -------
        list of CDMSDataset
            The retrieved datasets. Each successful dataset has its `filePath`
            set; failures carry a `fetchError`.
        """
        return self._datasets.fetch(path, kwargs)

    def buildDataSearch(
        self,
        **kwargs,
    ) -> tuple(str, str):
        """Construct the catalog paths and query string used to search for CDMS
        datasets. Arguments can take the following forms: 
         - string, number: search for a single exact match
         - string containing `*`: do a wildcard search
         - list: search for all items in the list
         - slice: search for all items between slice.start and slice.stop

        Users rarely call this directly; see 
        [findData][CDMSDataCatalog.CDMSDataCatalog.findData] for examples.

        Parameters
        ----------
        **kwargs
            CDMS metadata selectors (e.g. `Facility`, `nFridgeRun`, `ProdType`,
            `ProdTag`, `nMergeLevel`, `Series`, `ProdStep`, `filename`, `query`)
            plus additional metadata query parameters.

        Returns
        -------
        tuple of (str, str)
            The search path and the query string.
        """
        return self._datasets.build_data_search(**kwargs) 

    def findData(self, query: str = None, dofetch: bool = False, fetchargs: dict[str, str] = {}, **kwargs) -> list[CDMSDataset]:
        """Find datasets using predefined CDMS keyword selectors.

        Parameters
        ----------
        query : str, optional
            An explicit datacat query. If omitted, the query is built entirely
            from `**kwargs`.
        dofetch : bool, default False
            If `True`, fetch all resulting datasets to local disk.
        fetchargs : dict, optional
            Keyword arguments forwarded to `fetch` when `dofetch` is `True`.
        **kwargs
            CDMS metadata selectors; see `buildDataSearch`.

        Returns
        -------
        list of CDMSDataset
            Datasets matching the query.

        Examples
        --------
        Find all noise files for a facility and fridge run:

        >>> dc.findData(Facility='CUTE', nFridgeRun=14, ProdStep='BatNoise')

        Get all submerged science data from a release and download it:

        >>> dc.findData(ProdTag='v5.9.3', nMergeLevel=1, nDataType=0,
        ...             dofetch=True)
        """
        return self._datasets(query, dofetch, fetchargs, kwargs)

    # ==================================================================
    # Group operations
    # ==================================================================
    def mkgroup(
        self,
        path: str,
        parents: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Create a new group.

        The group is created with a default `{"State": "Open"}` metadata entry,
        merged with any provided `metadata`.

        Parameters
        ----------
        path : str
            Full path to the new group.
        parents : bool, default False
            If `True`, create any missing higher-level groups.
        metadata : dict of str to str, optional
            Additional metadata to associate with the group.

        Raises
        ------
        FileExistsError
            If a group already exists at `path`.
        """
        self._groups.create(path, parents, metadata)

    def getgroup(self, path: str, site: str = "All") -> CDMSGroup:
        """Retrieve a fully populated group by path.

        Parameters
        ----------
        path : str
            Path to the group.
        site : str, default "All"
            Site filter.

        Returns
        -------
        CDMSGroup
            The group wrapper for the requested path.
        """
        return self._groups.get(path, site)

    def add_files_to_group(self, path: str, file_paths: Iterable[str]) -> None:
        """Add one or more dataset files to an open group.

        Parameters
        ----------
        path : str
            Path to the target group. Must be in an "Open" state.
        file_paths : iterable of str
            Dataset paths to add. Each may be a catalog path or a disk path
            containing exactly one `/CDMS/` segment.

        Raises
        ------
        ValueError
            If the group is closed or a path has an unrecognized format.
        """
        self._groups.add_files(path, file_paths)

    def remove_files_from_group(self, group_name: str, paths: list[str]) -> None:
        """Remove datasets from a group.

        Parameters
        ----------
        group_name : str
            Full path to the group to modify.
        paths : list of str
            Dataset paths to remove. May be catalog or disk paths, and may
            include wildcards.
        """
        self._groups.remove_files(group_name, paths)

    def retrieve_files_from_group(
        self, path: str, num_datasets: int = 1_000_000_000
    ) -> list[CDMSDataset]:
        """Retrieve the datasets associated with a group.

        Parameters
        ----------
        path : str
            Path to the group.
        num_datasets : int, optional
            Maximum number of datasets to return. Defaults to
            [`DEFAULT_MAX_DATASETS`][CDMSDataCatalog.constants.DEFAULT_MAX_DATASETS].

        Returns
        -------
        list of CDMSDataset
            The datasets linked to the group, or an empty list on failure.
        """
        return self._groups.retrieve_files(path, num_datasets) 

    def close_group(self, path: str) -> None:
        """Close a group, preventing further file additions.

        Parameters
        ----------
        path : str
            Path to the group to close.
        """
        self._groups.close(path)

    def open_group(self, path: str) -> None:
        """Open a group, allowing files to be added.

        Parameters
        ----------
        path : str
            Path to the group to open.
        """
        self._groups.open(path)

    def group_is_open(self, group: CDMSGroup) -> bool:
        """Determine whether a group is currently open.

        Parameters
        ----------
        group : CDMSGroup
            The group to inspect.

        Returns
        -------
        bool
            `True` if the group's `"State"` metadata is `"Open"`.
        """
        return self._groups.is_open(group)

    # ==================================================================
    # Dependency operations
    # ==================================================================
    def getDependents(self, dep_container: CDMSDataset | CDMSGroup, dep_type: str, max_depth: int, chunk_size: int, **kwargs) -> list:
        """Retrieve dependents of a container, subject to depth and chunk size.

        Parameters
        ----------
        dep_container : CDMSDataset or CDMSGroup or object
            The parent container to retrieve dependents from.
        dep_type : str
            The type of dependents to retrieve.
        max_depth : int
            Maximum depth of the dependency chain to traverse.
        chunk_size : int
            Number of dependents to retrieve per request.
        **kwargs
            Additional arguments forwarded to the client.

        Returns
        -------
        list
            The retrieved dependents.
        """
        return self._dependents.get(dep_container, dep_type, max_depth, chunk_size, kwargs)

    def getNextDependents(self, dep_container: CDMSDataset | CDMSGroup, **kwargs) -> list:
        """Retrieve the next page of dependents for a container.

        Parameters
        ----------
        dep_container : CDMSDataset or CDMSGroup
            The parent container.
        **kwargs
            Additional arguments forwarded to the client.

        Returns
        -------
        list
            The next set of dependents.
        """
        return self._dependents.get_next(dep_container, **kwargs)

    def checkDependencyCycles(
            self, dep_container: CDMSDataset | CDMSGroup, dep_type: str, dep_dss: list = None, dep_grps: list = None
    ):
        """Check for dependency cycles that would result from an addition.

        Parameters
        ----------
        dep_container : CDMSDataset or CDMSGroup
            The parent container to check.
        dep_type : str
            The type of dependents to be added.
        dep_dss : list, optional
            Candidate dependent datasets (version PKs required).
        dep_grps : list, optional
            Candidate dependent groups.

        Returns
        -------
        graphlib.TopologicalSorter
            The topological sorter representing the dependency graph.
        """
        return self._dependents.check_cycles(dep_container, dep_type, dep_dss, dep_grps)

    def addDependents(
        self,
        dep_container: CDMSDataset | CDMSGroup,
        dep_type: str,
        dep_datasets: list = None,
        dep_groups: list = None,
        **kwargs,
    ) -> None:
        """Attach new dependents to a container.

        Parameters
        ----------
        dep_container : CDMSDataset or CDMSGroup or object
            The parent container to add dependents to.
        dep_type : str
            The type of dependents to add.
        dep_datasets : list, optional
            Datasets to attach as children (version PKs required).
        dep_groups : list, optional
            Groups to attach as children.
        **kwargs
            Additional arguments forwarded to the client.
        """
        self._dependents.add(dep_container, dep_type, dep_dataset, dep_groups, kwargs)

    def removeDependents(
        self,
        dep_container: CDMSDataset | CDMSGroup,
        dep_type: str,
        dep_datasets: list = None,
        dep_groups: list = None,
        **kwargs,
    ) -> None:
        """Remove dependents from a container.

        Parameters
        ----------
        dep_container : CDMSDataset or CDMSGroup or object
            The parent container to remove dependents from.
        dep_type : str
            The type of dependents to remove.
        dep_datasets : list, optional
            Datasets to detach.
        dep_groups : list, optional
            Groups to detach.
        **kwargs
            Additional arguments forwarded to the client.
        """
        self._dependents.remove(dep_container, dep_type, dep_datasets, dep_groups, kwargs)

    # ==================================================================
    # CDMS-specific discovery
    # ==================================================================
    def getProductionInfo(
        self,
        facility: str = "",
        fridgeRun: str = "",
        processingType: str = "",
        productionTagList: list | None = None,
        verbose: bool = True,
    ):
        """Get production tags and their metadata.

        Parameters
        ----------
        facility : str
            Facility name, e.g. `"CUTE"` (required).
        fridgeRun : int or str
            Fridge run number, or `"last"` for the most recent (required).
        processingType : str, default "release"
            Either `"release"` or `"test"`.
        productionTagList : list of str, optional
            Restrict results to these tags. If `None`, all tags are returned.
        verbose : bool, default True

        Returns
        -------
        dict
            Mapping of `{production_tag: metadata}`.

        Examples
        --------
        >>> dc.getProductionInfo('CUTE', 'last', 'release')
        """

        return self._discovery.get_production_info(
                facility,
                fridgeRun, 
                processingType, 
                productionTagList if productionTagList is not None else [],
                verbose
        )

    def getSeriesInfo(
        self,
        facility: str,
        fridgeRun: int | str,
        seriesList: list[str] = [],
        isInSLAC: bool = True,
        dataTypeList: list[int] = [],
        beginDateTime: str = "",
        endDateTime: str = "",
        includeMetadata: bool = True,
        verbose: bool = True,
    ) -> dict | list:
        """Get the series list and metadata for a facility/run.

        Parameters
        ----------
        facility : str
            Facility name (required).
        fridgeRun : int or str
            Fridge run number, or `"last"` (required).
        seriesList : list of str, optional
            Restrict to these series. If `None`, all series are returned.
        isInSLAC : bool, default True
            Return only series present at SLAC (per `nIsInSLAC` metadata).
        dataTypeList : list of int, optional
            Restrict to these data types.
        beginDateTime : str, optional
            Lower time bound: `YYMMDD`, `YYMMDD_HHMM`, or `YYMMDD_HHMMSS`.
        endDateTime : str, optional
            Upper time bound, same format as `beginDateTime`.
        includeMetadata : bool, default True
            If `True` return `{series: metadata}`; otherwise a list of series
            numbers.
        verbose : bool, default True

        Returns
        -------
        dict or list
            A dict if `includeMetadata` is `True`, otherwise a list.
        """
        return self._discovery.get_series_info(
                facility,
                fridgeRun,
                seriesList if seriesList is not None else [],
                isInSLAC,
                dataTypeList if dataTypeList is not None else [],
                beginDateTime,
                endDateTime,
                includeMetadata,
                verbose,
        )

    def getRawDataList(
        self,
        facility: str,
        fridgeRun: int | str,
        location: str = "SLAC",
        seriesList: list | None = None,
        dataTypeList: list | None = None,
        beginDateTime: str = "",
        endDateTime: str = "",
        verbose: bool = True,
    ):
        """Get the raw data file list for a facility/run.

        Parameters
        ----------
        facility : str
            Facility name (required).
        fridgeRun : int or str
            Fridge run number, or `"last"` (required).
        location : str, default "SLAC"
            Site where the data files reside.
        seriesList : list of str, optional
            Restrict to these series. If `None`, all series are returned.
        dataTypeList : list of int, optional
            Restrict to these data types.
        beginDateTime : str, optional
            Lower time bound.
        endDateTime : str, optional
            Upper time bound.
        verbose : bool, default True

        Returns
        -------
        dict
            Mapping of `{series: [raw file resources]}`.
        """
        return self._discovery.get_raw_data_list(
            facility,
            fridgeRun,
            location,
            seriesList if seriesList is not None else [],
            dataTypeList if dataTypeList is not None else [],
            beginDateTime,
            endDateTime,
            verbose,
        )

    def getProcessedDataList(
        self,
        facility: str,
        fridgeRun: int | str,
        productionTag: str,
        fileType: str = "submerged",
        location: str = "SLAC",
        seriesList: list[str] = [],
        dataTypeList: list[int] = [],
        beginDateTime: str = "",
        endDateTime: str = "",
        outputSeriesDictFormat: bool = False,
        verbose: bool = True,
    ):
        """Get the processed data file list for a production tag.

        Parameters
        ----------
        facility : str
            Facility name (required).
        fridgeRun : int or str
            Fridge run number, or `"last"` (required).
        productionTag : str
            Production tag, e.g. `"Prodv5.9.3"` (required).
        fileType : str, default "submerged"
            One of `"unmerged"`, `"submerged"`, `"merged"`, or `"noise"`.
        location : str, default "SLAC"
            Site where the data files reside.
        seriesList : list of str, optional
            Restrict to these series. If `None`, all series are returned.
        dataTypeList : list of int, optional
            Restrict to these data types.
        beginDateTime : str, optional
            Lower time bound.
        endDateTime : str, optional
            Upper time bound.
        outputSeriesDictFormat : bool, default False
            If `True` return `{series: [files]}`; otherwise a flat list.
        verbose : bool, default True

        Returns
        -------
        dict or list
            A dict if `outputSeriesDictFormat` is `True`, otherwise a list.
        """
        return self._discovery.get_processed_data_list(
            facility,
            fridgeRun,
            productionTag,
            fileType,
            location,
            seriesList if seriesList is not None else [],
            dataTypeList if dataTypeList is not None else [],
            beginDateTime,
            endDateTime,
            outputSeriesDictFormat,
            verbose,
        )

    def getFacilityName(self, facility_id: int) -> str:
        """Convert a numeric facility ID to its facility name.

        Parameters
        ----------
        facility_id : int
            The 2-digit series-name prefix identifying the facility.

        Returns
        -------
        str
            The facility name, or an empty string if not recognized.
        """
        return facilities.facilitiy_name(facility_id)

    def getLastFridgeRunNumber(self, facility: str = "CUTE"):
        """Get the most recent fridge run number for a facility.

        Parameters
        ----------
        facility : str, default "CUTE"
            The facility to inspect.

        Returns
        -------
        int
            The most recent fridge run number, or
            [`RUN_NOT_FOUND`][CDMSDataCatalog.facilities.RUN_NOT_FOUND] if none
            is found.
        """
        return facilities.last_fridge_number(self._core, facility)
