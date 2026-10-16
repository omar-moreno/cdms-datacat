"""Dataset operations for the CDMS Data Catalog.

This module provides the [`Datasets`][CDMSDataCatalog.datasets.Datasets] class,
which handles dataset-level operations: retrieving datasets by path, searching
the catalog, registering new datasets, adding dataset locations, resolving path
patterns to dataset objects, building CDMS-specific search queries, and
fetching datasets to local disk.

`Datasets` is composed on top of a single
[`CatalogCore`][CDMSDataCatalog.core.CatalogCore] instance, from which it
obtains client access and the default fetch directory. It is consumed directly
by the top-level facade and is injected into the group and discovery
components. CDMS-specific query construction is delegated to the stateless
`paths` and `facilities` helper modules; downloading is delegated to the
`fetchdata` function.
"""

import logging

from datacat.client import Client
from datacat.model import Dataset

from .CDMSDataset import CDMSDataset
from .core import CatalogCore
from .path_utils import normalize_path
from . import paths, facilities
from .fetch import fetchdata

logger = logging.getLogger(__name__)

class Datasets:
    """Dataset-level operations for the CDMS Data Catalog.

    Provides retrieval, search, registration, resolution, query construction,
    and fetching of datasets. All catalog access is delegated to the underlying
    [`CatalogCore`][CDMSDataCatalog.core.CatalogCore] client; CDMS-specific
    query construction is delegated to the stateless `paths` and `facilities`
    modules; downloading is delegated to
    [`fetchdata`][CDMSDataCatalog.fetch.fetchdata].

    Parameters
    ----------
    dc : CatalogCore
        Core catalog instance providing client access and shared low-level
        operations.

    Attributes
    ----------
    dc : CatalogCore
        The core catalog instance backing all operations.

    Notes
    -----
    The `client` and `default_fetchdir` properties proxy through to the
    underlying `CatalogCore`. They serve two purposes: they are used internally
    as the canonical accessors for the client and fetch directory, and they
    allow a `Datasets` instance to satisfy the "catalog-like" interface expected
    by [`fetchdata`][CDMSDataCatalog.fetch.fetchdata] (which reads
    ``client`` and ``default_fetchdir`` off the object passed to it).
    """

    def __init__(self, dc: CatalogCore) -> None:
        self.dc = dc

    @property
    def client(self) -> Client:
        """The underlying data catalog client.

        Proxied from the backing [`CatalogCore`][CDMSDataCatalog.core.CatalogCore].
        Used as the canonical client accessor throughout this class, and read by
        [`fetchdata`][CDMSDataCatalog.fetch.fetchdata] when a `Datasets` instance
        is passed to it.

        Returns
        -------
        datacat.client.Client
            The initialized catalog client.
        """
        return self.dc.client

    @property
    def default_fetchdir(self) -> str:
        """Absolute path to the default local fetch directory.

        Proxied from the backing
        [`CatalogCore`][CDMSDataCatalog.core.CatalogCore].

        Returns
        -------
        str
            The default fetch directory path.
        """
        return self.dc.default_fetchdir

    def get(self, path: str, site: str = "All") -> CDMSDataset:
        """Convert a data catalog path (string) to a full `CDMSDataset` object.

        Parameters
        ----------
        path : str
            Data catalog path to a dataset e.g. ``"/CDMS/SNOLAB/..."``.
        site : str, default "All"
            Site filter (e.g. ``"SLAC"``, ``"SNOLAB"``). ``"All"`` returns
            the dataset regardless of the site.

        Returns
        -------
        CDMSDataset
            Fully populated dataset wrapper.
        """
        path = normalize_path(path)
        raw_ds: Dataset = self.dc.client.path(path, site=site)
        return CDMSDataset.fromDataset(raw_ds)

    def search(self, path: str, site: str = "All", getallmetadata: bool = False, **kwargs) -> list[CDMSDataset]:
        """Search the data catalog and return sorted CDMSDatasets.

        See https://github.com/slaclab/datacat/wiki/Search-Syntax for the
        query/wildcard syntax.

        Search results do not contain full metadata unless requested via the
        `show` keyword. If `getallmetadata` is ``True``, each hit is re-fetched
        via [`get`][CDMSDataCatalog.datasets.Datasets.get] to attach its full
        metadata — this incurs a separate round trip per hit, so prefer `show`
        when possible.

        Parameters
        ----------
        path : str
            Full or partial path, may include wildcards.
        site : str, default "All"
            Restrict results to a site if given.
        getallmetadata : bool, default False
            If ``True``, re-fetch each hit via 
            [`get`][CDMSDataCatalog.datasets.Datasets.get] for full metadata.
        **kwargs
            Passed through to ``datacat.client.Client.search``.

        Returns
        -------
        list of CDMSDataset
            Results sorted by path.


        Warnings
        --------
        Enabling `getallmetadata` issues one additional catalog round trip per
        result and can be very slow for large result sets. Prefer passing a
        `show` list to retrieve only the metadata fields you need.
        """
        path = normalize_path(path)
        results: list[Dataset] = self.client.search(path, site=site, **kwargs)
        # Results come back unsorted; sort by path for stable, predictable output.
        results.sort(key=lambda res: res.path)
        if getallmetadata:
            return [self.get(res.path, site=site) for res in results]
        return [CDMSDataset.fromDataset(res) for res in results]

    def resolve_datasets(self, paths: list[str]) -> list[Dataset]:
        """Resolve dataset paths (possibly with wildcards) into dataset objects.

        Each path may be a catalog path or a filesystem path containing a
        ``/CDMS/`` segment (which is converted to a catalog path). Paths without
        wildcards are looked up directly; paths containing ``*`` or ``?`` are
        expanded via a catalog search.

        Parameters
        ----------
        paths : list of str
            Dependent dataset paths. Each may be a data catalog path or a disk
            path, and may include wildcards ("*", "?").

        Returns
        -------
        list
            Resolved dataset objects.

        Raises
        ------
        TypeError
            If `paths` is not a list. 
        """
        if not isinstance(paths, list):
            raise TypeError(f"'paths' must be a list, but got {type(paths).__name__}")

        dependents: list = []

        for path in paths:
            # If it's a disk path containing "/CDMS/", convert to a catalog path.
            if path.count("/CDMS/") == 1:
                path_after_cdms = path.split("/CDMS/")[1]
                path = f"/CDMS/{path_after_cdms}"

            if ("*" not in path) and ("?" not in path):
                # Direct path to a dataset (no wildcards)
                dependents.append(self.get(path))
            else:
                # Wildcard search
                head, _, tail = path.rpartition("/")
                query_path = head + "/" if head else ""
                query = f"name=~'{tail}'"
                results = self.dc.client.search(query_path, query=query)
                dependents.extend(results)

        return dependents

    def add(self, cdms_ds: CDMSDataset, replace: bool = True, catch_errors: bool = False) -> None:
        """Register a new `CDMSDataset` entry in the catalog.

        Ensures the parent directory exists, optionally replaces an existing
        entry at the same path, and creates the dataset. For datasets not
        located at SLAC, size and checksum are recorded.

        Parameters
        ----------
        cdms_ds : CDMSDataset
            The dataset to add.
        replace : bool, default True
            If ``True``, overwrite an existing entry at the same path.
        catch_errors : bool, default True
            If ``True``, errors are reported and suppressed. If ``False``, errors
            are allowed to propagate.

        Raises
        ------
        ValueError
            If the dataset's ``dataType`` is ``"DatacatQuery"``, which cannot be
            committed.

        Warnings
        --------
        When `replace` is ``True`` and an entry already exists at the target
        path, the existing dataset is **deleted** before the new one is created.
        This is a destructive operation on the prior entry.
        """
        if cdms_ds.dataType == "DatacatQuery":
            raise ValueError(
                'Cannot commit dataset with type "DatacatQuery", invalid type'
            )
        try:
            path: str = normalize_path(cdms_ds.relativePath)
            if not self.client.exists(path):
                self.dc.mkdir(path, parents=True)
            ds_exists: bool = self.dc.client.exists(path + "/" + cdms_ds.datasetName)
            if ds_exists:
                if replace:
                    logger.warning("Replacing existing dataset: %s/%s", path, cdms_ds.datasetName)
                    self.dc.rm(path + "/" + cdms_ds.datasetName)
                else:
                    logger.info("Skipping existing dataset: %s/%s", path, cdms_ds.datasetName)

            # Try to get size and checksum for files that are not at SLAC.
            # OM: Why is this necessary to do by site?
            if not ds_exists or replace:
                if cdms_ds.site == "SLAC":
                    ds: Dataset = self.dc.client.mkds(
                        path,
                        cdms_ds.datasetName,
                        cdms_ds.fileType,
                        cdms_ds.fileFormat,
                        versionMetadata=cdms_ds.metadata,
                        resource=cdms_ds.filePath,
                        site=cdms_ds.site,
                    )
                else:
                    ds = self.dc.client.mkds(
                        path,
                        cdms_ds.datasetName,
                        cdms_ds.fileType,
                        cdms_ds.fileFormat,
                        versionMetadata=cdms_ds.metadata,
                        resource=cdms_ds.filePath,
                        site=cdms_ds.site,
                        size=cdms_ds.filesize,
                        checksum=cdms_ds.crcchecksum,
                    )
                cdms_ds.rawDataset = ds
        except Exception:
            if catch_errors:
                logger.exception("Could not create dataset")
            else:
                raise

    def add_loc(self, path : str, site : str, resource : str, catch_errors : bool = False):
        """Add a new physical location to an existing registered dataset.

        Registers an additional site/resource pair for a dataset that already
        exists in the catalog, so the same dataset can be resolved from multiple
        physical locations.

        Parameters
        ----------
        path : str
            Target dataset path in the catalog.
        site : str
            Site where the dataset physically resides (e.g. ``"OSN"``,
            ``"SLAC"``).
        resource : str
            The file resource path at the given site.
        catch_errors : bool, default False
            If ``True``, errors are reported and suppressed. If ``False``, errors
            are allowed to propagate.
        """
        try:
            ds_exists: bool = self.client.exists(path)
            if ds_exists:
                self.client.path(path, versionId="current")
                self.client.mkloc(path, site, resource)
                ds_return = self.client.path(path, versionId="current")
                try:
                    for loc in ds_return.locations:
                        logger.info("Dataset site: %s at location %s ", loc.site, loc.resource)
                except Exception:
                    logger.exception("Dataset location cannot be found")
            else:
                logger.warning("Dataset does not exist")
        except Exception:
            if catch_errors:
                logger.exception("Could not add data location to Dataset")
            else:
                raise

    def fetch(self, path : str | CDMSDataset | list, **kwargs) -> list[CDMSDataset]:
        """Fetch (download) the dataset(s) at `path` to local disk.

        Only files not already present locally are downloaded. See
        [`fetchdata`][CDMSDataCatalog.fetch.fetchdata] for the accepted forms of
        `path` and the full set of keyword arguments. If `dest` is not provided,
        it defaults to
        [`default_fetchdir`][CDMSDataCatalog.datasets.Datasets.default_fetchdir].

        Parameters
        ----------
        path : str or CDMSDataset or list
            The file(s) to download. May be a catalog path, a wildcard query
            string, a [`CDMSDataset`][CDMSDataCatalog.CDMSDataset.CDMSDataset],
            or a list of these.
        **kwargs
            Additional arguments forwarded to
            [`fetchdata`][CDMSDataCatalog.fetch.fetchdata] (e.g. ``dest``,
            ``destRelative``, ``maxthreads``, ``force``).

        Returns
        -------
        list of CDMSDataset
            The retrieved datasets. Each successful dataset has its ``filePath``
            set; failures carry a ``fetchError``.


        """
        kwargs.setdefault("dest", self.dc.default_fetchdir)
        return fetchdata(self, path, **kwargs)

    def build_data_search(
        self,
        Facility : str = "*",
        nFridgeRun : str = "*",
        ProdType : str = "*",
        ProdTag : str = "*",
        nMergeLevel : int | None = None,
        Series : str = "*",
        ProdStep : str | None = None,
        filename : str | None = None,
        query : str | None = None,
        **kwargs,
    ) -> tuple[str, str]:
        """Construct the catalog path and query string for CDMS datasets.

        Arguments beginning with a capital letter generally correspond to
        metadata fields. Each such argument may take one of several forms: an
        exact value, a string containing ``*`` for a wildcard, a list to match
        any item, or a slice to match a range.

        Users rarely call this directly; see
        [`find_data`][CDMSDataCatalog.datasets.Datasets.find_data] for examples.

        Parameters
        ----------
        Facility : str, default "*"
            Name of the data-taking facility.
        nFridgeRun : int or str, default "*"
            Numerical fridge run, or ``"last"`` for the most recent.
        ProdType : str, default "*"
            One of ``"raw"``, ``"test"``, or ``"release"``.
        ProdTag : str, default "*"
            Production tag for ``"test"`` or ``"release"`` data.
        nMergeLevel : int, optional
            ``0`` for unmerged, ``1`` for submerged, ``2`` for merged.
        Series : str, default "*"
            Series number as a string (including underscore).
        ProdStep : str, optional
            One of ``"BatDIDV"``, ``"BatNoise"``, ``"BatRoot"``, ``"BatCalib"``,
            ``"Cut"``, ``"PyNoise"``, ``"PyTemplate"``, ``"PyPkl"``,
            ``"PyPklRRQ"``.
        filename : str, optional
            The name of the actual file.
        query : str, optional
            An additional catalog search query to include.
        **kwargs
            Additional metadata selectors, appended to the query.

        Returns
        -------
        tuple of (str, str)
            The search path and the query string.

        Raises
        ------
        ValueError
            If ``nFridgeRun="last"`` is requested without a concrete `Facility`.


        """
        query_phrases : list[str] = [query] if query else []

        # For each parameter, if it's a "special" query argument, replace it
        # with '*' in the path and append a query phrase instead.
        def checksimple(param_, name_ : str, force : bool = False):
            if force or not paths.is_simple_arg(param_):
                query_phrases.append(paths.build_query_phrase(name_, param_))
                return "*"
            return param_

        # handle special 'last' case for nFridgeRun
        if nFridgeRun == "last" or nFridgeRun == -1:
            if not paths.is_simple_arg(
                Facility, allowstar=False, allownone=False
            ):
                raise ValueError("Can't find last fridge run without facility")
            nFridgeRun = facilities.last_fridge_run_number(self.dc, Facility)

        Facility = checksimple(Facility, "Facility")
        nFridgeRun = checksimple(nFridgeRun, "nFridgeRun")
        ProdType = checksimple(ProdType, "ProdType")
        ProdTag = checksimple(ProdTag, "ProdTag")
        nMergeLevel = checksimple(nMergeLevel, "nMergeLevel")
        Series = checksimple(Series, "Series", force=Series is not None)
        ProdStep = checksimple(ProdStep, "ProdStep", force=ProdStep is not None)

        path : str = paths.getpath_data(
            Facility,
            nFridgeRun,
            ProdType,
            ProdTag,
            nMergeLevel,
            Series,
            ProdStep,
            filename,
        )
        if path.endswith("*") and not path.endswith("**"):
            path += "*"

        # additional query args from kwargs
        for k, v in kwargs.items():
            query_phrases.append(paths.build_query_phrase(k, v))

        return path, " and ".join(query_phrases)

    def find_data(self, query : str | None = None, dofetch : bool = False, fetchargs : dict | None = None, **kwargs) -> list[CDMSDataset]:
        """Find datasets using predefined CDMS keyword selectors.

        Builds a search from CDMS metadata keywords (via
        [`build_data_search`][CDMSDataCatalog.datasets.Datasets.build_data_search]),
        runs it, and optionally downloads the results.

        Parameters
        ----------
        query : str, optional
            An explicit catalog query. If omitted, the query is built entirely
            from `**kwargs`.
        dofetch : bool, default False
            If ``True``, fetch all resulting datasets to local disk.
        fetchargs : dict, optional
            Keyword arguments forwarded to
            [`fetch`][CDMSDataCatalog.datasets.Datasets.fetch] when `dofetch` is
            ``True``. Defaults to an empty mapping.
        **kwargs
            CDMS metadata selectors; see
            [`build_data_search`][CDMSDataCatalog.datasets.Datasets.build_data_search].

        Returns
        -------
        list of CDMSDataset
            Datasets matching the query.

        Examples
        --------
        Find all noise files for a facility and fridge run:

        >>> datasets.find_data(Facility='CUTE', nFridgeRun=14, ProdStep='BatNoise')

        Get all submerged science data from a release and download it:

        >>> datasets.find_data(ProdTag='v5.9.3', nMergeLevel=1, nDataType=0,
        ...                    dofetch=True)

        """
        if fetchargs is None:
            fetchargs = {}
        site: str = kwargs.pop("site", "All")
        path, built_query = self.build_data_search(query=query, **kwargs)
        logger.debug("Searching path %s with additional query '%s'", path, built_query)
        results : list[CDMSDataset] = self.search(path, site=site, query=built_query)
        if dofetch:
            results = self.fetch(results, **fetchargs)
        return results
