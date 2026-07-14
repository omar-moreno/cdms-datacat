"""Primary data catalog user interface"""

import logging
from enum import Enum
from collections.abc import Iterable

from datacat.model import Dataset
from pathlib import Path

from . import paths
from .CDMSDataset import CDMSDataset
from .CDMSGroup import CDMSGroup
from .fetch import fetchdata
from .path_utils import normalize_path
from .core import CatalogCore
from .groups import Groups
from .datasets import Datasets
from .dependents import Dependents
from .facilities import facility_name

__all__ = ["CDMSDataCatalog"]

log = logging.getLogger(__name__)


class DepType(Enum):
    PREDECESSOR = "predecessor"
    SUCCESSOR = "successor"


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

    def __init__(
        self,
        config_file: Path | str | None= None,
        default_fetchdir: Path | str | None = None,
    ) -> None:
        """
        Initialze the CDMSDataCatalog instance.

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

        Notes
        -----
        The configuration file must follow Python's configparser syntax.
        All settings including url, auth_type, auth_key_id, auth_secret_key, and
        default_fetchdir should be placed in the [defaults] section.
        """
        self._core = CatalogCore(config_file, default_fetchdir)
        self.client = self._core.client
        self.default_fetchdir = self._core.default_fetchdir

        self._groups = Groups(self.client)
        self._datasets = Datasets(self.client)
        self._dependents = Dependents(self.client)

    def ls(self, path: str = "/CDMS") -> list[str] | None:
        self._core.ls(path)

    def exist(
        self, path: str, version_id: str | None = None, site: str | None = None
    ) -> bool:
        return self._core.exists(path, version_id, site)

    def rm(self, path: str, recursive: bool = False) -> None:
        self._core.rm(path, recursive)

    def mkdir(
        self,
        path: str,
        parents: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self._core.mkdir(path, parents, metadata)

    def add_metadata(
        self, path: str, metadata: dict[str, str], replace: bool = False
    ) -> bool:
        return self._core.add_metadata(path, metadata, replace)

    def mkgroup(
        self,
        path: str,
        parents: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self._groups.create(path, parents, metadata)


    def getgroup(self, path, site="All"):
        return self._groups.get(path, site)

    def add_files_to_group(self, path: str, file_paths: Iterable[str]) -> None:
        self._groups.add_files(path, file_paths)

    def remove_files_from_group(self, group_name: str, paths: list[str]) -> None:
        self._groups.remove_files(group_name, paths)

    def retrieve_files_from_group(
        self, path: str, num_datasets: int = 1_000_000_000
    ) -> list[CDMSDataset]:
       return self._groups.retrieve_files(path, num_datasets) 

    def close_group(self, path: str):
        self._groups.close(path)

    def open_group(self, path: str):
        self._groups.open(path)

    def group_is_open(self, group: CDMSGroup) -> bool:
        return self._groups.is_open(group)

    def search(self, path, site="All", getallmetadata=False, **kwargs):
        return self._datasets.search(path, site, getallmetadata, kwargs)

    def get(self, path, site="All"):
        return self._datasets.get(path, site)

    def add(self, CDMSds, replace=True, catch_errors=True):
        self._datasets.add(CDMSds, replace, catch_errors)

    def addLoc(self, path, site, resource, catch_errors=True):
        self._datasets.add_loc(path, site, resource, catch_errors)

    def fetch(self, path, **kwargs):
        return self._datasets.fetch(path, kwargs)

    def getDependents(self, dep_container, dep_type, max_depth, chunk_size, **kwargs):
        return self._dependents.get(dep_container, dep_type, max_depth, chunk_size, kwargs)

    def getNextDependents(self, dep_container, **kwargs):
        """
         Retrieve next dependents attached to container object.
        :param dep_container: Parent container object you wish to get next dependents from
        :return: list of dependent objects attached to container object
        """
        return self._dependents.get_next(dep_container, **kwargs)

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
        return self._dependents.check_cycles(dep_container, dep_type, dep_dss, dep_grps)

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
        self._dependents.add(dep_container, dep_type, dep_dataset, dep_groups, kwargs)

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
        self._dependents.remove(dep_container, dep_type, dep_datasets, dep_groups, kwargs)

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
        return self._datasets.build_data_search(Facility, nFridgeRun, ProdType, ProdTag, nMergeLevel, Series, ProdStep, filename, query, kwargs)

    def findData(self, query=None, dofetch=False, fetchargs={}, **kwargs):
        return self._datasets(query, dofetch, fetchargs, kwargs)

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
            print("ERROR: Problem reading datacatalog path: " + datacatalog_path)
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
            print("ERROR: Problem reading datacatalog path: " + datacatalog_path)
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
                        print('\nWARNING: Format of "beginDateTime" not understood...')
                        print("It should be YYMMDD, YYMMDD_HHMM or YYMMDD_HHMMSS")
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
                        print('\nWARNING: Format of "endDateTime" not understood...')
                        print("It should be YYMMDD, YYMMDD_HHMM or YYMMDD_HHMMSS")
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

        print("Will search the file list for " + str(len(series_list)) + " series!")
        print("Be patient! It may take a while...")

        # ======================
        # Get files
        # ======================

        # loop and get files
        for series in series_list:
            # get files
            datacatalog_path = "/CDMS/" + facility + "/" + run_name + "/Raw/" + series
            raw_datasets = []

            try:
                raw_datasets = self.client.children(datacatalog_path, site=location)
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
                print('Use function "getProductionInfo" to get list of available tags!')
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
            print('Use function "getProductionInfo" to get list of available tags.')
            return

        if seriesList and not isinstance(seriesList, list):
            seriesList = [seriesList]

        if dataTypeList and not isinstance(dataTypeList, list):
            dataTypeList = [dataTypeList]

        # ======================
        # Get datasets
        # ======================

        # full path
        base_path += "/" + productionType + "/" + productionTag + "/" + fileType
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
            dataset_list = self.search(base_path, site=location, query=query, show=show)
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
        return facilitiy_name(facility_id)

    def getLastFridgeRunNumber(self, facility="CUTE"):
        return last_fridge_number(self._core, facility)
