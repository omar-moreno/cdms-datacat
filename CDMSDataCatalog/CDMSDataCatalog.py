"""Primary data catalog user interface"""

import logging
import pathlib
from importlib.resources import files
from typing import Dict, Optional

import datacat
from datacat import client_from_config, config_from_file

from . import paths
from .CDMSDataset import CDMSDataset
from .CDMSGroup import CDMSGroup
from .fetch import fetchdata, get_default_fetchdir

__all__ = ["CDMSDataCatalog"]

log = logging.getLogger(__name__)


def normalize_group_path(path: str) -> str:
    """
    Ensures that the given path starts with '/CDMS/' and is properly
    formatted.


    This function performs the following checks and modifications:
    1. If the path is empty, it returns '/CDMS' as the default.
    2. If the path does not start with '/', a '/' is prepended.
    3. If the path does not start with '/CDMS', '/CDMS' is prepended (removing
       any leading slashes before).
    4. If the path already starts with '/CDMS', it is returned unchanged,
       ensuring that there are no redundant prefixes.
    5. Trailing slashes are removed from the final path.

    Args:
        path (str): The path to be corrected. Can be either absolute or
                    relative.

    Returns:
        str: The corrected path, ensuring it starts with '/CDMS/' and has no
             trailing slashes.

    Example:
        >>> normalize_group_path("/CUTE/Raw/Run1")
        '/CDMS/CUTE/Raw/Run1'

        >> normalize_group_path("")
        '/CDMS'
    """

    # If the path is empty, return "/CDMS" as a default
    if not path:
        return "/CDMS"

    # Ensure the path starts with "/"
    if path[0] != "/":
        path = "/" + path

    # Check if the path starts with "/CDMS", otherwise add it
    if not path.startswith("/CDMS"):
        path = "/CDMS" + path.lstrip("/")

    # Remove the trailing slash and return the normalized path
    return path.rstrip("/")


def getFileFormat(filePath):
    return "".join(pathlib.Path(filePath).suffixes).strip(".")


class CDMSDataCatalog:
    """Data catalog client class.
    This is the primary class that users will interact with in the analysis
    environment.  The most useful methods are:

    * `ls`: list the contents of a directory
    * `get`: Get a `CDMSDataCatalog.CDMSDataset.CDMSDataset` for a fully qualified path
    * `search`: Search for matching datasets with a query syntax
    * `fetch`: Download datsets to local disk
    * `findData`: Search for datasets using pre-defined keywords.

    Attributes:
        default_fetchdir (str): local download top-level directory
        client (datacat.client.Client): Lower-level default SLAC client

    """

    def __init__(self, config_file=None, default_fetchdir=None):
        """##Constructor
        Args:
            config_file (str): location of config file with client settings
            default_fetchdir (str): root directory for downloading data

        The file specified by `config_file` must follow
        [configparser](https://docs.python.org/3/library/configparser.html)
        syntax.  All settings should be in the `[defaults]` section.
        Suggested approach is to copy `cfg/default.cfg` as a starting point.
        Recognized heys are:

        * url: base URL for accessing the catalog web interface
        * auth_type: web authentication standard
        * auth_key_id: authentication id
        * auth_secret_key: authentication public key
        * default_fetchdir: same as `default_fetchdir` argument


        """

        # load the configuration file
        if config_file is None:
            config_file = files("CDMSDataCatalog").joinpath("cfg/default.cfg")

        config = config_from_file(config_file)

        # determine default data fetchdir
        self.default_fetchdir = default_fetchdir
        if default_fetchdir is None:
            self.default_fetchdir = get_default_fetchdir()
            # see if it was specified in the config file
            try:
                self.default_fetchdir = config["defaults"]["default_fetchdir"]
            except KeyError:  # this is not in the config file
                pass

        self.client = client_from_config(config)

    def ls(self, path="/CDMS/"):
        """Return contents of a datacat path, by default look in /CDMS/"""
        path = normalize_group_path(path)
        try:
            return list(
                map(lambda child: child.path, self.client.children(path))
            )
            # for child in self.client.children(path):
            # print( child.path)
        except TypeError:
            print("Cannot ls, %s is a dataset" % path)
        except BaseException:
            print("Path does not exist")

    def exist(self, path, versionId=None, site=None):
        """Test if the given path exists in the data catalog.
        Note: This is NOT testing if the actual file exists on disk
        """
        path = normalize_group_path(path)
        do_exist = self.client.exists(path, versionId, site)
        return do_exist

    def rm(self, path, recursive=False, verbose=True):
        """Remove an entry from the catalog. Obviously this should only be
        used by experts with extreme caution!

        Args:
            path (str): The full data catalog entry path
            recursive (bool): If the path is a directory, delete everything
                below it.  You probably can't delete folders with subentrires
                if this is False...
            verbose (bool): provide more information about what's happening
        """
        path = normalize_group_path(path)

        if verbose:
            print(path)
        if recursive:
            try:
                if type(self.client.path(path)) == datacat.model.Dataset:
                    response = self.client.rmds(path)
                    print(response)
                    return
            except Exception:
                print("Couldn't delete %s" % path)
                return

            else:
                for child in self.client.children(path):
                    self.rm(child.path, recursive=True)

                ctype = "folder"
                if type(self.client.path(path)) == datacat.model.Group:
                    ctype = "group"

                if verbose:
                    print(path)
                try:
                    response = self.client.rmdir(path, type=ctype)
                    print(response)
                except Exception:
                    print("Couldn't delete %s" % path)
                return
        else:
            try:
                if type(self.client.path(path)) == datacat.model.Dataset:
                    self.client.rmds(path)
                else:
                    self.client.rmdir(path)
            except Exception as e:
                print(e)
                raise IOError("Couldn't delete " + path)

    def mkgroup(
        self,
        path: str,
        parents: bool = False,
        metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Create a new group at the specified path.

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
        path = normalize_group_path(path)

        # Attempt to create the group, handle the case where it already exists
        if not self.exist(path):
            self.client.mkgroup(path, parents=parents, metadata=metadata)
            return True
        else:
            print(f"WARNING: group {path} already exists")

        return False

    def getgroup(self, path, site="All"):
        """Convert a path (string) to a full CDMSGroup object"""
        path = normalize_group_path(path)
        rawgroup = self.client.path(path, site=site)
        return CDMSGroup.fromGroup(rawgroup)

    def mkdir(
        self, path, parents=False, metadata=None
    ):  ### ELA: modified this function to include metadata argument
        """Create a new directory
        Args:
            path (str): full path to the new directory
            parents (bool): create any missing higher-level directories on the
                way (similar to `mkdir -p`)
        """
        path = normalize_group_path(path)
        self.client.mkdir(
            path, parents=parents, metadata=metadata
        )  ### ELA: see above comment...
        return

    def search(self, path, site="All", getallmetadata=False, **kwargs):
        """Call `client.search` and return sorted CDMSDatasets

        See https://github.com/slaclab/datacat/wiki/Search-Syntax for the
        nominal syntax for path wildcards and query operators. (NB: the syntax
        for returning folders rather than datasets doesn't seem to work!)

        Normally search results don't contain metadata unless specified by the
        `show` optional argument.  if `getallmetadata` is True, call `get` on
        each hit returned to get it's full metadata list.  This results in a
        separate round-trip query for each hit, so don't enable unless you
        need it; giving `show` is MUCH more efficient.

        Args:
            path (str): full or partial path to data, can include wildcards
            site (str): restrict results to site if given, else get all
            getallmetadata (bool): If True, call `get` after searching so that
                all metadata is attached to the resulting dataset
            **kwargs: all other arguments are passed to
                `datacat.client.Client.search`.

        Examples:
            Find all the merged processed data for CUTE run 14
            >>> dc.search('/CDMS/CUTE/R14/Processed/Releases/**',
            ...           query='nMergeLevel == 2')
        """
        path = normalize_group_path(path)
        results = self.client.search(path, site=site, **kwargs)
        # results come back unsorted, which is not what we want
        results.sort(key=lambda res: res.path)
        if getallmetadata:
            results = [self.get(res.path, site=site) for res in results]
        else:
            results = [CDMSDataset.fromDataset(res) for res in results]
        return results

    def get(self, path, site="All"):
        """Convert a path (string) to a full CDMSDataset object"""
        path = normalize_group_path(path)
        rawds = self.client.path(path, site=site)
        return CDMSDataset.fromDataset(rawds)

    def add(self, CDMSds, replace=True, catch_errors=True):
        """Add a new CDMSDataset entry to the catalog
        Args:
            CDMSds (CDMSDataset): The new dataset to add
            replace (bool):  If true, overwrite an existing entry at that path
            catch_errors (bool): If False, allow errors to propagate
        """
        if CDMSds.dataType == "DatacatQuery":
            raise ValueError(
                'Cannot commit dataset with type "DatacatQuery", invalid type'
            )
        try:
            path = normalize_group_path(CDMSds.relativePath)
            if not self.client.exists(path):
                self.mkdir(path, parents=True)
            DSexists = self.client.exists(path + "/" + CDMSds.datasetName)
            if DSexists:
                if replace:
                    print(
                        "Replacing existing dataset:",
                        path,
                        "/",
                        CDMSds.datasetName,
                    )
                    self.rm(path + "/" + CDMSds.datasetName)
                else:
                    print(
                        "Skipping existing dataset:",
                        path,
                        "/",
                        CDMSds.datasetName,
                    )

            #####################
            # This is to try and get size and checksum for files that are not at SLAC (as metadata)

            if not DSexists or replace:
                # Maybe a Cleaner way to implement if Crawler is before this (which I do not think it is)
                # if(scan_result =! {"scanStatus": "MISSING"}):
                if CDMSds.site == "SLAC":
                    ds = self.client.mkds(
                        path,
                        CDMSds.datasetName,
                        CDMSds.fileType,
                        CDMSds.fileFormat,
                        versionMetadata=CDMSds.metadata,
                        resource=CDMSds.filePath,
                        site=CDMSds.site,
                    )
                else:
                    ds = self.client.mkds(
                        path,
                        CDMSds.datasetName,
                        CDMSds.fileType,
                        CDMSds.fileFormat,
                        versionMetadata=CDMSds.metadata,
                        resource=CDMSds.filePath,
                        site=CDMSds.site,
                        size=CDMSds.filesize,
                        checksum=CDMSds.crcchecksum,
                    )
                CDMSds.rawDataset = ds
        except Exception as e:
            if catch_errors:
                print(e)
                print("Could not create dataset")
            else:
                raise

    def addLoc(self, path, site, resource, catch_errors=True):
        """Add a new dataset location to an existing registered dataset
        Args:
            path (str): Target Dataset path in the DataCatalog
            site (str): The site where the dataset physically resides (OSN, SLAC, ...)
            resource (str): The file resource path at the given site
        Return:
            A representation of the dataset that was just created.
        """
        try:
            DSexists = self.client.exists(path)
            if DSexists:
                ds_check = self.client.path(path, versionId="current")
                dsaddLoc = self.client.mkloc(path, site, resource)
                ds_return = self.client.path(path, versionId="current")
                try:
                    for loc in ds_return.locations:
                        print(
                            "Dataset site: %s at location %s "
                            % (loc.site, loc.resource)
                        )
                except:
                    print("Dataset location cannot be found")
            else:
                print("Dataset does not exist")

        except Exception as e:
            if catch_errors:
                print(e)
                print("Could not add data location to Dataset")
            else:
                raise

    def add_metadata(
        self, path: str, metadata: dict, replace: bool = False
    ) -> bool:
        """
        Adds or updates metadata for the specified container (folder, group).

        Args:
            path (str): The path to the folder or group.
            metadata (dict): The metadata to add or update.
            replace (bool): Whether to replace existing metadata (default is False).

        Returns:
            bool: True if metadata was successfully added or updated, False otherwise.
        """

        # Normalize the group path
        path = normalize_group_path(path)

        # Retrieve the container (folder, group) to add metadata to
        container = self.client.path(path)
        container_metadata = container.metadata

        existing_entries = set(metadata.keys()) & set(
            container_metadata.keys()
        )

        if existing_entries and not replace:
            print(
                f"The following metadata already exists: {existing_entries}. To override them, set 'replace=True'."
            )
            return False

        # Update the containers metadata with the new metadata
        container.metadata = metadata

        # Commit the changes
        self.client.patchdir(container.path, container)

        return True

    def fetch(self, path, **kwargs):
        """fetch (download) dataset at `path`.
        See `CDMSDataCatalog.fetch.fetchdata` for
        different possible forms for `path` and additional arguments"""
        kwargs.setdefault("dest", self.default_fetchdir)
        return fetchdata(self, path, **kwargs)

    def getDependents(
        self, dep_container, dep_type, max_depth, chunk_size, **kwargs
    ):
        """
        Retrieves dependents up to the provided "chunk_size" at a time, subject to "max_depth".

        :param dep_container: Parent container to get dependents from.
        :param dep_type: Type of dependents to get.
        :param max_depth: Depth of dependency chain.
        :param chunk_size: Total amount of dependents retrieved.
        :return: List of retrieved dependents.
        """
        if isinstance(dep_container, CDMSDataset):
            try:
                container = dep_container.rawDataset
                if hasattr(container, "versionMetadata"):
                    if container.versionMetadata.get("dependencyName"):
                        # refresh container for latest
                        container = self.client.path(
                            container.path,
                            versionId=container.versionId,
                            site="All",
                        )
            except Exception:
                raise ValueError(
                    "Unqualified dataset passed as dependency container"
                )
        elif isinstance(dep_container, CDMSGroup):
            try:
                container = dep_container.rawGroup
                if hasattr(container, "metadata"):
                    if container.metadata.get("dependencyName"):
                        # refresh container for latest
                        container = self.client.path(container.path)
            except Exception:
                raise ValueError(
                    "qualified group passed as dependency container"
                )
        else:
            container = dep_container
        return self.client.get_dependents(
            container, dep_type, max_depth, chunk_size, **kwargs
        )

    def getNextDependents(self, dep_container, **kwargs):
        """
         Retrieve next dependents attached to container object.
        :param dep_container: Parent container object you wish to get next dependents from
        :return: List of dependent objects attached to container object
        """
        if isinstance(dep_container, CDMSDataset):
            try:
                container = dep_container.rawDataset
            except Exception:
                raise ValueError(
                    "Unqualified dataset passed as dependency container"
                )
        elif isinstance(dep_container, CDMSGroup):
            try:
                container = dep_container.rawGroup
            except Exception:
                raise ValueError(
                    "Unqualified group passed as dependency container"
                )
        return self.client.get_next_dependents(container, **kwargs)

    def checkDependencyCycles(
        self, dep_container, dep_type, dep_dss=None, dep_grps=None
    ):
        """
        Check existing cycles in dep_container and if dependents are to be added.
            :param dep_container: Parent container object to add dependents to
            :param dep_type: Type of dependents to add
            :param dep_dss: The datasets we wish to use as children of the parent container
                VersionPKs are required for each dependent dataset.
            :param dep_grps: The groups we wish to use as children of the parent container
            :return ts: the topological sorter object in graphlib
        """
        return self.client.check_dependency_cycles(
            dep_container, dep_type, dep_dss, dep_grps
        )

    def addDependents(
        self,
        dep_container,
        dep_type,
        dep_datasets=None,
        dep_groups=None,
        **kwargs,
    ):
        """
         Attach new dependents to container object.
        :param dep_container: Parent container object to add dependents to
        :param dep_type: Type of dependents to add
        :param dep_datasets: The datasets we wish to use as children of the parent container
        VersionPKs are required for each dependent dataset.
        :param dep_groups: The groups we wish to use as children of the parent container
        """
        if isinstance(dep_container, CDMSDataset):
            try:
                container = dep_container.rawDataset
            except Exception:
                raise ValueError(
                    "Unqualified CDMSDataset passed as dependency container"
                )
        elif isinstance(dep_container, CDMSGroup):
            try:
                container = dep_container.rawGroup
            except Exception:
                raise ValueError(
                    "Unqualified CDMSGroup passed as dependency container"
                )
        else:
            container = dep_container
        dep_grps = []
        for group in dep_groups or []:
            if isinstance(group, CDMSGroup):
                try:
                    dep_grps.append(group.rawGroup)
                except Exception:
                    raise ValueError("Unqualified group passed as dependent")
            else:
                dep_grps.append(group)
        dep_dss = []
        for dataset in dep_datasets or []:
            if isinstance(dataset, CDMSDataset):
                try:
                    dep_dss.append(dataset.rawDataset)
                except Exception:
                    raise ValueError("Unqualified dataset passed as dependent")
            else:
                dep_dss.append(dataset)
        ret = self.client.add_dependents(
            container, dep_type, dep_dss, dep_grps, **kwargs
        )
        if isinstance(dep_container, CDMSDataset):
            dep_container.rawDataset = ret
        elif isinstance(dep_container, CDMSGroup):
            dep_container.rawGroup = ret

    def removeDependents(
        self,
        dep_container,
        dep_type,
        dep_datasets=None,
        dep_groups=None,
        **kwargs,
    ):
        """
        Remove dependents from container object provided
        :param dep_container: Parent container object to remove dependents from
        :param dep_type: Type of dependents to remove
        :param dep_datasets: The datasets we wish to remove from the parent container
        :param dep_groups: The groups we wish to remove from the parent container
        """
        if isinstance(dep_container, CDMSDataset):
            try:
                container = dep_container.rawDataset
            except Exception:
                raise ValueError(
                    "Unqualified dataset passed as dependency container"
                )
        elif isinstance(dep_container, CDMSGroup):
            try:
                container = dep_container.rawGroup
            except Exception:
                raise ValueError(
                    "Unqualified group passed as dependency container"
                )
        else:
            container = dep_container
        dep_grps = []
        for group in dep_groups or []:
            if isinstance(group, CDMSGroup):
                try:
                    dep_grps.append(group.rawGroup)
                except Exception:
                    raise ValueError("Unqualified group passed as dependent")
            else:
                dep_grps.append(group)
        dep_dss = []
        for dataset in dep_datasets or []:
            if isinstance(dataset, CDMSDataset):
                try:
                    dep_dss.append(dataset.rawDataset)
                except Exception:
                    raise ValueError("Unqualified dataset passed as dependent")
            else:
                dep_dss.append(dataset)
        ret = self.client.remove_dependents(
            container, dep_type, dep_dss, dep_grps, **kwargs
        )
        if isinstance(dep_container, CDMSDataset):
            dep_container.rawDataset = ret
        elif isinstance(dep_container, CDMSGroup):
            dep_container.rawGroup = ret

    def buildDataSearch(
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
        """Construct the data catalog path and query string for CDMS
        datasets. Arguments starting with a capital are generally directly
        equivalent to metadata arguments.  Arguments can take the following
        forms:

        * string, number: search for a single exact match
        * string containing `*`: do a wildcard search
        * list: search for all items in list
        * slice: search for all items between slice.start and slice.stop

        Users will rarely call this function directly.  For examples, see
        `CDMSDataCatalog.findData`

        Args:
            Facility (str): name of data-taking facility
            nFridgeRun (int): numerical fridge run or 'last' for most recent
            ProdType (str): one of 'raw', 'test', 'release'. `None` = 'raw'
                            '*' = 'test' or 'release'
            ProdTag (str): production tag for 'test' or 'release' data
            nMergeLevel (int): 0 for 'Unmerged',
                               1 for 'Submerged',
                               2 for 'Merged'
            Series (str): series number as a string (including underscore)
            ProdStep (str): One of 'BatDIDV', 'BatNoise', 'BatRoot', 'BatCalib', 'Cut', 'PyNoise', 'PyTemplate', 'PyPkl', 'PyPklRRQ'
            filename (str): the name of the actual file
            query (str): additional `datacat.client.Client.search` query.
                         See [here](https://github.com/slaclab/datacat/wiki/Search-Syntax)
                         for the syntax.
            **kwargs: additional metadata selectors. See the documentation
                      for the relevant `CDMSDataset` class for the list of
                      metadata

        Returns:
            tuple: Data Catalog search path and query as a `(str, str)` tuple

        TODO:
            * Convert data type string ('ba', cf', etc) to number
        """
        if query:
            query = [query]
        else:
            query = []

        # for each parameter, if it is a special query argument, replace
        # with '*' in the path
        def checksimple(param_, name_, query_, force=False):
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
            nFridgeRun = self.getLastFridgeRunNumber(Facility)

        Facility = checksimple(Facility, "Facility", query)
        nFridgeRun = checksimple(nFridgeRun, "nFridgeRun", query)
        ProdType = checksimple(ProdType, "ProdType", query)
        ProdTag = checksimple(ProdTag, "ProdTag", query)
        nMergeLevel = checksimple(nMergeLevel, "nMergeLevel", query)
        Series = checksimple(Series, "Series", query, force=Series is not None)
        ProdStep = checksimple(
            ProdStep, "ProdStep", query, force=ProdStep is not None
        )

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

        # handle additional query args from kwargs, convert to string
        # todo: handle nDataType here
        for k, v in kwargs.items():
            query.append(paths.build_query_phrase(k, v))
        query = " and ".join(query)

        return path, query

    def findData(self, query=None, dofetch=False, fetchargs={}, **kwargs):
        """Run a query to find data against the data catalog
        Args:
          query (str):  The datacat client query (filter) to run. Can be blank,
                        in which case it will be entirely built from kwargs.
          dofetch (bool): If True, call fetch on all the result data (i.e.,
                          find the corresponding files on local disk)
          fetchargs (dict): keyword arguments to be passed to `fetch.fetchdata`
          **kwargs:  Additional keyword arguments are interpreted as metadata
                     query parameters. See `CDMSDataCatalog.buildDataSearch`

        Returns:
            A list of CDMSDatasets matching the query

        Examples:
           Find all noise files for a given facility and fridge run:
           >>> dc.findData(Facility='CUTE', nFridgeRun=14, ProdStep='BatNoise')

           The same, but restricted to 'release' level data
           >>> dc.findData(Facility='CUTE', nFridgeRun=14, ProdStep='BatNoise',
           ...             ProdType='release')

           Find raw data entries for a series range:
           >>> dc.findData(Series=slice('23200300_000000', '23200305_000000'),
           ...             ProdType='raw')

           Get all submerged data entries from a release production:
           >>> dc.findData(ProdTag='v5.9.3', nMergeLevel=1)

           The same, but restrict to science data
           >>> dc.findData(ProdTag='v5.9.3', nMergeLevel=1, nDataType=0)

           Now download it to local disk (using default paths)
           >>> dc.findData(ProdTag='v5.9.3', nMergeLevel=1, nDataType=0,
           ...             dofetch=True)

           Download everything to the current working directory instead
           >>> dc.findData(ProdTag='v5.9.3', nMergeLevel=1, nDataType=0,
           ...             dofetch=True,
           ...             fetchargs=dict(dest='.', destRelative=False))
        """
        site = kwargs.pop("site", "All")
        path, query = self.buildDataSearch(**kwargs)
        # should we catch exceptions here, or let them bubble?
        log.debug("Searching path %s with additional query '%s'", path, query)
        datasets = self.search(path, site=site, query=query)
        if dofetch:
            datasets = self.fetch(datasets, **fetchargs)
        return datasets

    def getProductionInfo(
        self,
        facility="",
        fridgeRun="",
        processingType="",
        productionTagList=[],
        verbose=True,
    ):
        """Get production tag list and metadata

        Args:
            facility (str): 'CUTE', 'SLAC', 'NEXUS', etc.   (required)
            fridgeRun (int): 10, 11, etc  OR 'last (required)
            processingType (str): 'release' or 'test' (default: 'release')
            productionTagList (list of str): list of production tag such as
                Prodv9.5.3' (default: return all tags)
            verbose (bool): default: True

        Returns:
            dictionary of {production tag: metadata}

        Examples:
            Find all release tags for CUTE latest run
            >>> dc.getProductionInfo('CUTE', 'last', 'release')
        """
        # check arguments
        if not facility or not fridgeRun:
            print('Required arguments: "facility" and "fridgeRun"')
            return

        if not processingType:
            if verbose:
                print('No "processingType" provided. Will use "release"!')
            processingType = "release"

        output_dict = dict()

        # ====================
        # Build path
        # ====================

        # fridge run
        run_name = str(fridgeRun)
        if run_name == "last":
            run_number = self.getLastFridgeRunNumber(facility)
            if run_number == -999999:
                print("ERROR: unable to find last fridge run number!")
                return
            run_name = "R" + str(run_number)
            if verbose:
                print("Last Run: " + run_name)
        elif run_name[0] != "R":
            run_name = "R" + str(fridgeRun)

        datacatalog_path = "/CDMS/" + facility + "/" + run_name + "/Processed/"
        if processingType == "release":
            datacatalog_path = datacatalog_path + "Releases"
        elif processingType == "test":
            datacatalog_path = datacatalog_path + "Tests"
        else:
            print('ERROR: processingType should be either "release" or "test"')
            return output_dict

        # ====================
        # Get tags
        # ====================

        try:
            folder_list = self.client.children(datacatalog_path)
        except:
            print(
                "ERROR: Problem reading datacatalog path: " + datacatalog_path
            )
            return output_dict

        for datacat_folder in folder_list:

            # get metadata
            prod_tag = datacat_folder.name

            # filter
            if productionTagList:
                if prod_tag not in productionTagList:
                    continue

            folder_metadata = dict()
            if hasattr(datacat_folder, "metadata"):
                folder_metadata = dict(datacat_folder.metadata)

            # output
            output_dict[prod_tag] = folder_metadata

        return output_dict

    def getSeriesInfo(
        self,
        facility,
        fridgeRun,
        seriesList=[],
        isInSLAC=True,
        dataTypeList=[],
        beginDateTime=[],
        endDateTime=[],
        includeMetadata=True,
        verbose=True,
    ):
        """Get Series list and  metadata

        Args:
            facility (str): 'CUTE', 'SLAC', 'NEXUS', etc.   (required)
            fridgeRun (int): 10, 11, etc or 'last' (required)
            seriesList (list of str): [231217_1200, 231224_1010,etc]
                (default: return all series if empty)
            isInSLAC (bool): return only series at SLAC, based on nIsSLAC
                folder metadata (default: True)
            dataTypeList (list of int): [-1,0,1,2,..]
                (Default if emoty:  return all data types except test data -1)
            beginDateTime (str): YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS
            endDateTime (str): same as begin
            includeMetadata (bool): If True (default), return a dictionary,
                if False return a list of series numbers

        Returns:
            dict: if `includeMetadata` is True, map series to metadata
            list: if `includeMetadata` is False, list of series

        Todo:
            * refactor this function to use `paths`
        """

        output_dict = dict()
        output_list = list()  # if not metadata included, just list of series

        # =====================
        # Check arguments
        # =====================
        if not facility or not fridgeRun:
            print('Required arguments: "facility" and "fridgeRun"')
            return

        if dataTypeList and not isInSLAC:
            print(
                'ERROR: DataType can only be check if data in SLAC, please set "isInSLAC=True"!'
            )
            return

        if beginDateTime:
            beginDateTime = str(beginDateTime)
            if (
                len(beginDateTime) != 6
                and len(beginDateTime) != 11
                and len(beginDateTime) != 13
            ):
                print(
                    "ERROR: Format of beginDateTime available: YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS"
                )

        if endDateTime:
            endDateTime = str(endDateTime)
            if (
                len(endDateTime) != 6
                and len(endDateTime) != 11
                and len(endDateTime) != 13
            ):
                print(
                    "ERROR: Format of endDateTime available: YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS"
                )

        if dataTypeList and type(dataTypeList) != list:
            dataTypeList = [dataTypeList]

        if seriesList and type(seriesList) != list:
            seriesList = [seriesList]

        # =====================
        # Get Series folders
        # from data catalog
        # =====================

        # fridge run
        run_name = str(fridgeRun)
        if run_name == "last":
            run_number = self.getLastFridgeRunNumber(facility)
            if run_number == -999999:
                print("ERROR: unable to find last fridge run number!")
                return
            run_name = "R" + str(run_number)
            if verbose:
                print("Last Run: " + run_name)
        elif run_name[0] != "R":
            run_name = "R" + str(fridgeRun)

        # list of series
        datacatalog_path = "/CDMS/" + facility + "/" + run_name + "/Raw"
        folder_list = list()
        try:
            folder_list = self.client.children(datacatalog_path)
        except:
            print(
                "ERROR: Problem reading datacatalog path: " + datacatalog_path
            )
            return

        # ====================
        # Loop and Filter
        # ====================
        for datacat_folder in folder_list:

            # series name and metadata
            series = datacat_folder.name
            series_metadata = dict()
            if hasattr(datacat_folder, "metadata"):
                series_metadata = dict(datacat_folder.metadata)

            # check series name
            if len(series) != 13 and len(series) != 15:
                continue

            # check facility
            facility_id = int(series[0:2])
            facility_name = self.getFacilityName(facility_id)
            if facility_name != facility:
                continue

            # check if in series list
            if seriesList:
                if series not in seriesList:
                    continue

            # check in SLAC
            if isInSLAC:
                if ("nIsInSLAC" not in series_metadata) or (
                    "nIsInSLAC" in series_metadata
                    and int(series_metadata["nIsInSLAC"]) == 0
                ):
                    continue

            # check data type
            if dataTypeList and type(dataTypeList) != list:
                data_type = int(series_metadata["nDataType"])
                if data_type not in dataTypeList:
                    continue

            # check date range
            if beginDateTime or endDateTime:

                # remove underscore and facility id
                pos_underscore = series.find("_")
                series_time = series[pos_underscore - 6 :]
                series_time = series_time.replace("_", "")
                if len(series_time) == 10:
                    series_time += "00"

                # begin date
                if beginDateTime:
                    start = beginDateTime.replace("_", "")
                    if len(start) < 12:
                        for ii in range(0, 12 - len(start)):
                            start += "0"
                    if len(start) != len(series_time):
                        print(
                            '\nWARNING: Format of "beginDateTime" not understood...'
                        )
                        print(
                            "It should be YYMMDD, YYMMDD_HHMM or YYMMDD_HHMMSS"
                        )
                        return output_dict
                    if int(series_time) < int(start):
                        continue

                # end date
                if endDateTime:
                    end = endDateTime.replace("_", "")
                    if len(end) < 12:
                        for ii in range(0, 12 - len(end)):
                            end += "0"
                    if len(end) != len(series_time):
                        print(
                            '\nWARNING: Format of "endDateTime" not understood...'
                        )
                        print(
                            "It should be YYMMDD, YYMMDD_HHMM or YYMMDD_HHMMSS"
                        )
                        return output_dict
                    if int(series_time) > int(end):
                        continue

            # output
            if includeMetadata:
                output_dict[series] = series_metadata
            else:
                output_list.append(series)

        if includeMetadata:
            return output_dict
        else:
            return output_list

    def getRawDataList(
        self,
        facility,
        fridgeRun,
        location="SLAC",
        seriesList=[],
        dataTypeList=[],
        beginDateTime=[],
        endDateTime=[],
        verbose=True,
    ):
        """Get raw data file list

        Args:
            facility (str): 'CUTE', 'SLAC', 'NEXUS', etc.   (required)
            fridgeRun (int): 'last OR 10, 11, etc   (required)
            location (str): 'SLAC','SNOLAB', etc. [default: data files located at 'SLAC')
            seriesList (list of str): ['231217_1200', '231224_1010', ...]
                (default: return all series if empty)
            dataTypeList (list of int): [-1,0,1,2,..]
                (Default if empty:  return all data types except test data -1)
            beginDateTime (str): YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS
            endDateTime (str): same as begin

        Returns:
            dictionary of {series: [list of raw files in series]}

        Todo:
            * Have this function return list of datasets rather than SLAC paths
            * refactor to call `findData`
        """

        # initialize output
        output_dict = dict()

        # ======================
        # Check Input arguments
        # ======================
        if not facility or not fridgeRun:
            print('Required arguments: "facility" and "fridgeRun"')
            return

        # fridge run
        run_name = str(fridgeRun)
        if run_name == "last":
            run_number = self.getLastFridgeRunNumber(facility)
            if run_number == -999999:
                print("ERROR: unable to find last fridge run number!")
                return
            run_name = "R" + str(run_number)
        elif run_name[0] != "R":
            run_name = "R" + str(fridgeRun)

        if dataTypeList and type(dataTypeList) != list:
            dataTypeList = [dataTypeList]

        if seriesList and type(seriesList) != list:
            seriesList = [seriesList]

        # get list of series

        # if location is SLAC, then filter based on folder metadata
        isInSLAC = True
        if location != "SLAC":
            isInSLAC = False

        # ======================
        # Get list of series
        # ======================

        series_list = self.getSeriesInfo(
            facility=facility,
            fridgeRun=fridgeRun,
            seriesList=seriesList,
            isInSLAC=isInSLAC,
            dataTypeList=dataTypeList,
            beginDateTime=beginDateTime,
            endDateTime=endDateTime,
            includeMetadata=False,
        )

        if not series_list:
            print("WARNING: No series found! Check arguments")
            return

        print(
            "Will search the file list for "
            + str(len(series_list))
            + " series!"
        )
        print("Be patient! It may take a while...")

        # ======================
        # Get files
        # ======================

        # loop and get files
        for series in series_list:

            # get files
            datacatalog_path = (
                "/CDMS/" + facility + "/" + run_name + "/Raw/" + series
            )
            raw_datasets = []

            try:
                raw_datasets = self.client.children(
                    datacatalog_path, site=location
                )
            except:
                continue

            if not raw_datasets:
                continue

            file_list = []
            for dataset in raw_datasets:
                file_list.append(dataset.resource)

            output_dict[series] = file_list

        return output_dict

    def getProcessedDataList(
        self,
        facility,
        fridgeRun,
        productionTag,
        fileType="submerged",
        location="SLAC",
        seriesList=[],
        dataTypeList=[],
        beginDateTime="",
        endDateTime="",
        outputSeriesDictFormat=False,
        verbose=True,
    ):
        """Get processed data file list

        Args:
            facility (str): 'CUTE', 'SLAC', 'NEXUS', etc.   (required)
            fridgeRun (int): 'last',or  10, 11, etc  (required)
            productionTag (str): production tag, example 'Prodv5.9.3' (required)
            fileType (str): 'unmerged', 'submerged','merged','noise'
                            (default: 'submerged')
            location (str): 'SLAC','SNOLAB', etc.
                            [default: data files located at 'SLAC')
            seriesList (list of str): e.g. ['231217_1200', '231224_1010', ...]
                                      (default: return all series if empty)
            dataTypeList (list of int): [-1,0,1,2,..]
                (Default if empty:  return all data types except test data -1)
            beginDateTime (str): YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS
            endDateTime (str): same format as begin
            outputSeriesDictFormat (bool): if True return a dictionary with
                key=Series number, value: list of files

        Returns:
            dict: if outputSeriesDictFormat is True
            list: if outputSeriesDictFormat is False

        Todo:
            * refactor to use `findData`
        """

        # initlize ouput
        output_dict = dict()  # outputSeriesDictFormat=True
        output_list = list()  # outputSeriesDictFormat=False

        # ======================
        # Check Input arguments
        # ======================
        if not facility or not fridgeRun or not productionTag:
            print(
                'ERROR: Required arguments = "facility", "fridgeRun", and "productionTag"'
            )
            if not productionTag:
                print(
                    'Use function "getProductionInfo" to get list of available tags!'
                )
            return

        if not fileType:
            if verbose:
                print('No file type provided! Will use "submerged')
            fileType = "Submerged"

        if dataTypeList and type(dataTypeList) != list:
            dataTypeList = [dataTypeList]

        if seriesList and type(seriesList) != list:
            seriesList = [seriesList]

        fileType = fileType[0].capitalize() + fileType[1:]
        if (
            fileType != "Submerged"
            and fileType != "Merged"
            and fileType != "Unmerged"
            and fileType != "Noise"
        ):
            print(
                'ERROR: "fileType" argument should be "noise","merged", "submerged", or "unmerged"'
            )
            return

        if beginDateTime:
            beginDateTime = str(beginDateTime)
            if (
                len(beginDateTime) != 6
                and len(beginDateTime) != 11
                and len(beginDateTime) != 13
            ):
                print(
                    'ERROR: Format available for  "beginDateTime": YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS'
                )
                return
            beginDateTime = beginDateTime.replace("_", "")
            if len(beginDateTime) < 12:
                for ii in range(0, 12 - len(beginDateTime)):
                    beginDateTime += "0"

        if endDateTime:
            endDateTime = str(endDateTime)
            if (
                len(endDateTime) != 6
                and len(endDateTime) != 11
                and len(endDateTime) != 13
            ):
                print(
                    'ERROR: Format available for "endDateTime": YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS'
                )
                return
            endDateTime = endDateTime.replace("_", "")
            if len(endDateTime) < 12:
                for ii in range(0, 12 - len(endDateTime)):
                    endDateTime += "0"

        # get fridge run
        run_name = str(fridgeRun)
        if run_name == "last":
            run_number = self.getLastFridgeRunNumber(facility)
            if run_number == -999999:
                print("ERROR: unable to find last fridge run number!")
                return
            run_name = "R" + str(run_number)
            if verbose:
                print("Last Run: " + run_name)
        elif run_name[0] != "R":
            run_name = "R" + str(fridgeRun)

        # check if release or tests
        base_path = "/CDMS/" + facility + "/" + run_name + "/Processed"
        productionType = str()
        try:
            if self.exist(base_path + "/Releases/" + productionTag):
                productionType = "Releases"
            elif self.exist(base_path + "/Tests/" + productionTag):
                productionType = "Tests"
        except:
            print("ERROR: Problem accessing data catalog!")
            return

        if not productionType:
            print(
                'ERROR: No data with tag "'
                + productionTag
                + '" found in the datacatalog!'
            )
            print(
                'Use function "getProductionInfo" to get list of available tags.'
            )
            return

        if seriesList and not isinstance(seriesList, list):
            seriesList = [seriesList]

        if dataTypeList and not isinstance(dataTypeList, list):
            dataTypeList = [dataTypeList]

        # ======================
        # Get datasets
        # ======================

        # full path
        base_path += (
            "/" + productionType + "/" + productionTag + "/" + fileType
        )
        if fileType == "Unmerged":
            base_path += "/*"

        # build filter string
        query = "nIsJunk==0"
        if seriesList:
            query += ' and (Series=="{}"'.format(seriesList[0])
            for series in seriesList[1:]:
                query += ' or Series=="{}"'.format(series)
            query += ")"
        if dataTypeList:
            query += " and (nDataType==" + str(dataTypeList[0])
            for data_type in dataTypeList[1:]:
                query += " or nDataType==" + str(data_type)
            query += ")"
        if beginDateTime:
            query += " and nSeriesDateTime>=" + str(beginDateTime)
        if endDateTime:
            query += " and nSeriesDateTime<=" + str(endDateTime)

        show = ["Series"]
        dataset_list = []
        try:
            dataset_list = self.search(
                base_path, site=location, query=query, show=show
            )
        except:
            print("ERROR: Problem accessing data catalog!")
            print(
                "Perhaps the files were produced prior January 2020 and do not have the proper metadata?"
            )
            return

        if not dataset_list:
            print(
                'WARNING: No processed file found for "'
                + productionTag
                + '". Check data catalog!'
            )
            return

        # loop datasets
        for dataset in dataset_list:
            series = dataset.metadata["Series"]
            file_name = dataset.filePath
            if outputSeriesDictFormat:
                if series not in output_dict:
                    output_dict[series] = []
                output_dict[series].append(file_name)
            else:
                output_list.append(file_name)

        if outputSeriesDictFormat:
            return output_dict
        else:
            return output_list

    def getFacilityName(self, facility_id):
        """Convert numeric facility ID (series name 2-digit prefix) to string
        Args:
            facility_id (int): the ID to convert
        Returns:
            string: name of facility or empty string if not found.
        """

        facility = str()

        # list of facilities
        facilities_dict = {
            1: "Soudan",
            2: "UCB",
            3: "CWRU",
            4: "UFL",
            5: "TAMU",
            6: "Queens",
            7: "UMN",
            8: "Denver",
            9: "SLAC",
            21: "TRIUMF",
            22: "FNAL",
            23: "CUTE",
            24: "SNOLAB",
            25: "NEXUS",
            26: "TUNL",
            51: "DMC",
            99: "DAQTesting",
        }

        if facility_id in facilities_dict:
            facility = facilities_dict[facility_id]

        return facility

    def getLastFridgeRunNumber(self, facility="CUTE"):
        """Get the number for the most recent fridge run for `facility`.
        If any error is encountered, return -999999
        Args:
            facility (str): facility name
        Returns:
            int: most recent fridge run number or -999999
        """

        last_run = -999999

        # base path
        base_path = "/CDMS/" + facility

        # run list
        folder_list = list()
        try:
            folder_list = self.client.children(base_path)
        except:
            print(f'ERROR: Unable to read datacatalog path "{base_path}"!')
            return last_run

        if not folder_list:
            print(f"ERROR: No fridge run found in {datacat_path}")
            return last_run

        for datacat_folder in folder_list:
            run = datacat_folder.name
            try:
                last_run = max(last_run, int(run[1:]))
            except ValueError:  # run is not a number?
                pass

        return last_run
