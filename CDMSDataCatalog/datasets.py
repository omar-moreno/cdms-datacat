"""Dataset operations for the CDMS Data Catalog.

This module provides the :class:`Datasets` class which handles dataset-level
operations: retrieving datasets by path, searching, registering new datasets,
adding dataset locations, resolving path patterns to dataset objects, building
CDMS-specific queries, and fetching datasets to local disk.
"""

from .CDMSDataset import CDMSDataset
from .core import CatalogCore
from .path_utils import normalize_path

class Datasets:
    def __init__(self, dc, path_module, facilities_module, fetch_fn) -> None:
        self.dc = dc
        #self.paths = paths_module
        #self.facilities_module = facilities_module
        #self._fetch = fetch_fn

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
