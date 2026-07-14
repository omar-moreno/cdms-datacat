"""Dataset operations for the CDMS Data Catalog.

This module provides the :class:`Datasets` class which handles dataset-level
operations: retrieving datasets by path, searching, registering new datasets,
adding dataset locations, resolving path patterns to dataset objects, building
CDMS-specific queries, and fetching datasets to local disk.
"""

from .CDMSDataset import CDMSDataset
from .core import CatalogCore
from .path_utils import normalize_path
from . import paths
from . import facilities
from fetch import fetchdata

class Datasets:
    def __init__(self, dc) -> None:
        self.dc = dc

    def get(self, path: str, site: str = "All") -> CDMSDataset:
        """Convert a path (string) to a full CDMSDataset object.

        Parameters
        ----------
        path : str
            Data catalog path to a dataset e.g. /CDMS/SNOLAB/
        site : str, default "All"
            Site filter (e.g. "SLAC", "SNOLAB"). "All" returns a dataset 
            regardless of the site.

        Returns
        -------
        CDMSDataset
            Fully populated dataset wrapper.
        """
        path = normalize_path(path)
        raw_ds = self.dc.client.path(path, site=site)
        return CDMSDataset.fromDataset(raw_ds)

    def search(self, path: str, site: str = "All", getallmetadata: bool = False, **kwargs) -> list[CDMSDataset]:
        """Search the data catalog and return sorted CDMSDatasets.
        
        See https://github.com/slaclab/datacat/wiki/Search-Syntax for the
        query/wildcard syntax.

        Normally search results don't contain full metadata unless requested
        via the ``show`` argument. If ``getallmetadata`` is True, ``get`` is
        called on each hit to attach its full metadata list — this incurs a
        separate round trip per hit, so prefer ``show`` when possible.

        Parameters
        ----------
        path : str
            Full or partial path, may include wildcards.
        site : str, default "All"
            Restrict results to a site if given.
        getallmetadata : bool, default False
            If True, re-fetch each hit via :meth:`get` for full metadata.
        **kwargs
            Passed through to ``datacat.client.Client.search``.

        Returns
        -------
        list of CDMSDataset
            Results sorted by path.

        """
        path = normalize_path(path)
        results = self.dc.client.search(path, site=site, **kwargs)
        if getallmetadata:
            return [self.get(res.path, site=site) for res in results]
        return [CDMSDataset.fromDataset(res) for res in results]

    def resolve_datasets(self, path: list[str]) -> list[Dataset]:
        """Resolve dataset paths (possibly with wildcards) into dataset objects.

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
            If ``paths`` is not a list. 
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

    def add(self, cdms_ds, replace: bool = True, catch_errors: bool = True) -> None:
        """Add a new CDMSDataset entry to the catalog.

        Parameters
        ----------
        cdms_ds : CDMSDataset
            The dataset to add.
        replace : bool, default True
            If True, overwrite an existing entry at the same path.
        catch_errors : bool, default True
            If False, allow errors to propagate instead of being printed.
        """
        if cdms_ds.dataType == "DatacatQuery":
            raise ValueError(
                'Cannot commit dataset with type "DatacatQuery", invalid type'
            )
        try:
            path = normalize_path(cdms_ds.relativePath)
            if not self.dc.client.exists(path):
                self.dc.mkdir(path, parents=True)
            ds_exists = self.dc.client.exists(path + "/" + cdms_ds.datasetName)
            if ds_exists:
                if replace:
                    print("Replacing existing dataset:", path, "/", cdms_ds.datasetName)
                    self.dc.rm(path + "/" + cdms_ds.datasetName)
                else:
                    print("Skipping existing dataset:", path, "/", cdms_ds.datasetName)

            # Try to get size and checksum for files that are not at SLAC.
            # OM: Why is this necessary to do by site? 
            if not ds_exists or replace:
                if cdms_ds.site == "SLAC":
                    ds = self.dc.client.mkds(
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
        except Exception as e:
            if catch_errors:
                print(e)
                print("Could not create dataset")
            else:
                raise

    def add_loc(self, path, site, resource, catch_errors: bool = True):
        """Add a new dataset location to an existing registered dataset.

        Parameters
        ----------
        path : str
            Target dataset path in the catalog.
        site : str
            Site where the dataset physically resides (OSN, SLAC, ...).
        resource : str
            The file resource path at the given site.
        catch_errors : bool, default True
            If False, allow errors to propagate.
        """
        try:
            ds_exists = self.dc.client.exists(path)
            if ds_exists:
                self.dc.client.path(path, versionId="current")
                self.dc.client.mkloc(path, site, resource)
                ds_return = self.dc.client.path(path, versionId="current")
                try:
                    for loc in ds_return.locations:
                        print(
                            "Dataset site: %s at location %s "
                            % (loc.site, loc.resource)
                        )
                except Exception:
                    print("Dataset location cannot be found")
            else:
                print("Dataset does not exist")
        except Exception as e:
            if catch_errors:
                print(e)
                print("Could not add data location to Dataset")
            else:
                raise

    def fetch(self, path, **kwargs):
        """Fetch (download) the dataset(s) at ``path``.

        See the ``fetch`` module for the possible forms of ``path`` and
        additional keyword arguments.
        """
        kwargs.setdefault("dest", self.dc.default_fetchdir)
        return fetchdata(self.dc, path, **kwargs)

  def build_data_search(
        self,
        Facility="*",
        nFridgeRun="*",
        ProdType="*",
        ProdTag="*",
        nMergeLevel=None,
        Series="*",
        ProdStep=None,
        filename=None,
        query=None,
        **kwargs,
    ):
        """Construct the catalog path and query string for CDMS datasets.

        See the original docstring for argument semantics and forms.

        Returns
        -------
        tuple of (str, str)
            The search path and query string.
        """
        query = [query] if query else []

        # For each parameter, if it's a "special" query argument, replace it
        # with '*' in the path and append a query phrase instead.
        def checksimple(param_, name_, force=False):
            if force or not paths.is_simple_arg(param_):
                query.append(paths.build_query_phrase(name_, param_))
                return "*"
            return param_

        # handle special 'last' case for nFridgeRun
        if nFridgeRun == "last" or nFridgeRun == -1:
            if not paths.is_simple_arg(
                Facility, allowstar=False, allownone=False
            ):
                raise ValueError("Can't find last fridge run without facility")
            nFridgeRun = self.facilities.last_fridge_run_number(self.dc, Facility)

        Facility = checksimple(Facility, "Facility")
        nFridgeRun = checksimple(nFridgeRun, "nFridgeRun")
        ProdType = checksimple(ProdType, "ProdType")
        ProdTag = checksimple(ProdTag, "ProdTag")
        nMergeLevel = checksimple(nMergeLevel, "nMergeLevel")
        Series = checksimple(Series, "Series", force=Series is not None)
        ProdStep = checksimple(ProdStep, "ProdStep", force=ProdStep is not None)

        path = paths.getpath_data(
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
            query.append(self.paths.build_query_phrase(k, v))

        return path, " and ".join(query)

    def find_data(self, query=None, dofetch=False, fetchargs=None, **kwargs):
        """Run a query to find data against the catalog.

        Parameters
        ----------
        query : str, optional
            The datacat client query. May be blank (built entirely from kwargs).
        dofetch : bool, default False
            If True, fetch all result datasets to local disk.
        fetchargs : dict, optional
            Keyword arguments passed to :meth:`fetch`.
        **kwargs
            Metadata query parameters; see :meth:`build_data_search`.

        Returns
        -------
        list of CDMSDataset
            Datasets matching the query.
        """
        if fetchargs is None:
            fetchargs = {}
        site = kwargs.pop("site", "All")
        path, query = self.build_data_search(**kwargs)
        logger.debug("Searching path %s with additional query '%s'", path, query)
        datasets = self.search(path, site=site, query=query)
        if dofetch:
            datasets = self.fetch(datasets, **fetchargs)
        return datasets
