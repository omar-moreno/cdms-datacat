"""CDMS-specific data-discovery routines for the CDMS Data Catalog.

This module provides the :class:`Discovery` class, which implements the
higher-level, CDMS-domain-specific query helpers for locating production
information, series metadata, and raw/processed data file lists. These
routines build catalog paths and queries from CDMS conventions (facilities,
fridge runs, production tags, series naming, date-time encoding) and delegate
the actual catalog access to a :class:`~.datasets.Datasets` instance and the
underlying core client.
"""

import logging

from . import facilities
from .core import CatalogCore
from .datasets import Datasets

logger = logging.getLogger(__name__)

class Discovery:
    """CDMS-specific data-discovery operations.

    Parameters
    ----------
    dc : CatalogCore
        Core catalog instance used for direct client access.
    datasets : Datasets
        Datasets instance used for searching the catalog with CDMS queries.
    """

    def __init__(self, dc: CatalogCore, datasets: Datasets) -> None:
        self.dc = dc
        self.datasets = datasets

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _resolve_run_name(self, facility, fridge_run: int | str, verbose=True):
        """Resolve a fridge-run identifier into a run folder name (e.g. "R14").

        Handles the "last" special case by querying the catalog for the most
        recent run number, and normalizes plain run numbers by prefixing "R".

        Parameters
        ----------
        facility : str
            Facility name (needed to resolve "last").
        fridge_run : int or str
            Run number, or "last" for the most recent run.
        verbose : bool, default True
            If True, print the resolved run name when using "last".

        Returns
        -------
        str or None
            The run folder name (e.g. "R14"), or None if "last" was requested
            but no run could be found.
        """
        run_name = str(fridge_run)
        if run_name == "last":
            run_number = facilities.last_fridge_run_number(self.dc, facility)
            if run_number == facilities.RUN_NOT_FOUND:
                logger.error("ERROR: unable to find last fridge run number!")
                return None
            run_name = "R" + str(run_number)
            if verbose:
                print("Last Run: " + run_name)
        elif run_name and run_name[0] != "R":
            run_name = "R" + str(fridge_run)
        return run_name

    @staticmethod
    def _as_list(value):
        """Coerce a scalar into a single-element list; leave lists unchanged.

        Returns the value unchanged if it is falsy (empty list, "", etc.).
        """
        if value and not isinstance(value, list):
            return [value]
        return value

    @staticmethod
    def _normalize_datetime(value):
        """Normalize a YYMMDD[_HHMM[SS]] string to a zero-padded 12-char form.

        Returns
        -------
        str or None
            The normalized 12-character datetime string, or None if the input
            was empty. Returns the (invalid) padded value as-is if the length
            is unexpected; callers validate lengths separately.
        """
        if not value:
            return None
        value = str(value).replace("_", "")
        if len(value) < 12:
            value = value.ljust(12, "0")
        return value

    # ------------------------------------------------------------------
    # Production info
    # ------------------------------------------------------------------
    def get_production_info(
        self,
        facility="",
        fridgeRun="",
        processingType="",
        productionTagList=[],
        verbose=True,
    ):
        """Get production tag list and metadata.

        Parameters
        ----------
        facility : str
            'CUTE', 'SLAC', 'NEXUS', etc. (required)
        fridgeRun : int or str
            10, 11, etc. OR 'last' (required)
        processingType : str
            'release' or 'test' (default: 'release')
        productionTagList : list of str
            List of production tags such as 'Prodv9.5.3' (default: all tags).
        verbose : bool, default True

        Returns
        -------
        dict
            Mapping of {production tag: metadata}.
        """
        if not facility or not fridgeRun:
            print('Required arguments: "facility" and "fridgeRun"')
            return

        if not processingType:
            if verbose:
                print('No "processingType" provided. Will use "release"!')
            processingType = "release"

        output_dict = dict()

        run_name = self._resolve_run_name(facility, fridgeRun, verbose)
        if run_name is None:
            return

        datacatalog_path = "/CDMS/" + facility + "/" + run_name + "/Processed/"
        if processingType == "release":
            datacatalog_path = datacatalog_path + "Releases"
        elif processingType == "test":
            datacatalog_path = datacatalog_path + "Tests"
        else:
            print('ERROR: processingType should be either "release" or "test"')
            return output_dict

        try:
            folder_list = self.dc.client.children(datacatalog_path)
        except Exception:
            print("ERROR: Problem reading datacatalog path: " + datacatalog_path)
            return output_dict

        for datacat_folder in folder_list:
            prod_tag = datacat_folder.name

            if productionTagList and prod_tag not in productionTagList:
                continue

            folder_metadata = dict()
            if hasattr(datacat_folder, "metadata"):
                folder_metadata = dict(datacat_folder.metadata)

            output_dict[prod_tag] = folder_metadata

        return output_dict

    # ------------------------------------------------------------------
    # Series info
    # ------------------------------------------------------------------
    def get_series_info(
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
        """Get series list and metadata.

        Parameters
        ----------
        facility : str
            'CUTE', 'SLAC', 'NEXUS', etc. (required)
        fridgeRun : int or str
            10, 11, etc. or 'last' (required)
        seriesList : list of str
            e.g. ['231217_1200', '231224_1010'] (default: all series).
        isInSLAC : bool, default True
            Return only series at SLAC (based on nIsInSLAC folder metadata).
        dataTypeList : list of int
            [-1, 0, 1, 2, ...] (default: all types except test data -1).
        beginDateTime : str
            YYMMDD, YYMMDD_HHMM, or YYMMDD_HHMMSS.
        endDateTime : str
            Same format as begin.
        includeMetadata : bool, default True
            If True return a dict {series: metadata}; if False return a list
            of series numbers.
        verbose : bool, default True

        Returns
        -------
        dict or list
            Dict if ``includeMetadata`` is True, else a list of series.
        """
        output_dict = dict()
        output_list = list()

        if not facility or not fridgeRun:
            print('Required arguments: "facility" and "fridgeRun"')
            return

        if dataTypeList and not isInSLAC:
            print(
                'ERROR: DataType can only be check if data in SLAC, please set '
                '"isInSLAC=True"!'
            )
            return

        # Validate date-time formats (original only warned; behavior preserved)
        if beginDateTime:
            beginDateTime = str(beginDateTime)
            if len(beginDateTime) not in (6, 11, 13):
                print(
                    "ERROR: Format of beginDateTime available: "
                    "YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS"
                )

        if endDateTime:
            endDateTime = str(endDateTime)
            if len(endDateTime) not in (6, 11, 13):
                print(
                    "ERROR: Format of endDateTime available: "
                    "YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS"
                )

        dataTypeList = self._as_list(dataTypeList)
        seriesList = self._as_list(seriesList)

        run_name = self._resolve_run_name(facility, fridgeRun, verbose)
        if run_name is None:
            return

        datacatalog_path = "/CDMS/" + facility + "/" + run_name + "/Raw"
        try:
            folder_list = self.dc.client.children(datacatalog_path)
        except Exception:
            print("ERROR: Problem reading datacatalog path: " + datacatalog_path)
            return

        for datacat_folder in folder_list:
            series = datacat_folder.name
            series_metadata = dict()
            if hasattr(datacat_folder, "metadata"):
                series_metadata = dict(datacat_folder.metadata)

            # check series name
            if len(series) != 13 and len(series) != 15:
                continue

            # check facility
            facility_id = int(series[0:2])
            if facilities.facility_name(facility_id) != facility:
                continue

            # check if in series list
            if seriesList and series not in seriesList:
                continue

            # check in SLAC
            if isInSLAC:
                if ("nIsInSLAC" not in series_metadata) or (
                    int(series_metadata["nIsInSLAC"]) == 0
                ):
                    continue

            # check data type
            # NOTE: preserved original condition, but see the flagged bug below.
            if dataTypeList and type(dataTypeList) != list:
                data_type = int(series_metadata["nDataType"])
                if data_type not in dataTypeList:
                    continue

            # check date range
            if beginDateTime or endDateTime:
                pos_underscore = series.find("_")
                series_time = series[pos_underscore - 6 :]
                series_time = series_time.replace("_", "")
                if len(series_time) == 10:
                    series_time += "00"

                if beginDateTime:
                    start = self._normalize_datetime(beginDateTime)
                    if len(start) != len(series_time):
                        print('\nWARNING: Format of "beginDateTime" not understood...')
                        print("It should be YYMMDD, YYMMDD_HHMM or YYMMDD_HHMMSS")
                        return output_dict
                    if int(series_time) < int(start):
                        continue

                if endDateTime:
                    end = self._normalize_datetime(endDateTime)
                    if len(end) != len(series_time):
                        print('\nWARNING: Format of "endDateTime" not understood...')
                        print("It should be YYMMDD, YYMMDD_HHMM or YYMMDD_HHMMSS")
                        return output_dict
                    if int(series_time) > int(end):
                        continue

            if includeMetadata:
                output_dict[series] = series_metadata
            else:
                output_list.append(series)

        return output_dict if includeMetadata else output_list

    # ------------------------------------------------------------------
    # Raw data list
    # ------------------------------------------------------------------
    def get_raw_data_list(
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
        """Get raw data file list.

        Parameters
        ----------
        facility : str
            'CUTE', 'SLAC', 'NEXUS', etc. (required)
        fridgeRun : int or str
            'last' OR 10, 11, etc. (required)
        location : str, default "SLAC"
            'SLAC', 'SNOLAB', etc.
        seriesList : list of str
            (default: all series if empty)
        dataTypeList : list of int
            (default: all data types except test data -1)
        beginDateTime : str
            YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS
        endDateTime : str
            Same as begin.
        verbose : bool, default True

        Returns
        -------
        dict
            {series: [list of raw files in series]}.
        """
        output_dict = dict()

        if not facility or not fridgeRun:
            print('Required arguments: "facility" and "fridgeRun"')
            return

        run_name = self._resolve_run_name(facility, fridgeRun, verbose=False)
        if run_name is None:
            return

        dataTypeList = self._as_list(dataTypeList)
        seriesList = self._as_list(seriesList)

        # If location is SLAC, filter based on folder metadata.
        isInSLAC = location == "SLAC"

        series_list = self.get_series_info(
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
            "Will search the file list for " + str(len(series_list)) + " series!"
        )
        print("Be patient! It may take a while...")

        for series in series_list:
            datacatalog_path = (
                "/CDMS/" + facility + "/" + run_name + "/Raw/" + series
            )
            try:
                raw_datasets = self.dc.client.children(
                    datacatalog_path, site=location
                )
            except Exception:
                continue

            if not raw_datasets:
                continue

            output_dict[series] = [dataset.resource for dataset in raw_datasets]

        return output_dict

    # ------------------------------------------------------------------
    # Processed data list
    # ------------------------------------------------------------------
    def get_processed_data_list(
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
        """Get processed data file list.

        Parameters
        ----------
        facility : str
            'CUTE', 'SLAC', 'NEXUS', etc. (required)
        fridgeRun : int or str
            'last', or 10, 11, etc. (required)
        productionTag : str
            Production tag, e.g. 'Prodv5.9.3' (required).
        fileType : str, default "submerged"
            'unmerged', 'submerged', 'merged', or 'noise'.
        location : str, default "SLAC"
            'SLAC', 'SNOLAB', etc.
        seriesList : list of str
            (default: all series if empty)
        dataTypeList : list of int
            (default: all data types except test data -1)
        beginDateTime : str
            YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS
        endDateTime : str
            Same format as begin.
        outputSeriesDictFormat : bool, default False
            If True return {series: [files]}; else a flat list of files.
        verbose : bool, default True

        Returns
        -------
        dict or list
            Dict if ``outputSeriesDictFormat`` is True, else a list.
        """
        output_dict = dict()
        output_list = list()

        if not facility or not fridgeRun or not productionTag:
            print(
                'ERROR: Required arguments = "facility", "fridgeRun", and '
                '"productionTag"'
            )
            if not productionTag:
                print(
                    'Use function "getProductionInfo" to get list of available '
                    "tags!"
                )
            return

        if not fileType:
            if verbose:
                print('No file type provided! Will use "submerged')
            fileType = "Submerged"

        dataTypeList = self._as_list(dataTypeList)
        seriesList = self._as_list(seriesList)

        fileType = fileType[0].capitalize() + fileType[1:]
        if fileType not in ("Submerged", "Merged", "Unmerged", "Noise"):
            print(
                'ERROR: "fileType" argument should be "noise", "merged", '
                '"submerged", or "unmerged"'
            )
            return

        if beginDateTime:
            beginDateTime = str(beginDateTime)
            if len(beginDateTime) not in (6, 11, 13):
                print(
                    'ERROR: Format available for "beginDateTime": '
                    "YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS"
                )
                return
            beginDateTime = self._normalize_datetime(beginDateTime)

        if endDateTime:
            endDateTime = str(endDateTime)
            if len(endDateTime) not in (6, 11, 13):
                print(
                    'ERROR: Format available for "endDateTime": '
                    "YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS"
                )
                return
            endDateTime = self._normalize_datetime(endDateTime)

        run_name = self._resolve_run_name(facility, fridgeRun, verbose)
        if run_name is None:
            return

        # check if release or tests
        base_path = "/CDMS/" + facility + "/" + run_name + "/Processed"
        productionType = ""
        try:
            if self.dc.exists(base_path + "/Releases/" + productionTag):
                productionType = "Releases"
            elif self.dc.exists(base_path + "/Tests/" + productionTag):
                productionType = "Tests"
        except Exception:
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

        # full path
        base_path += "/" + productionType + "/" + productionTag + "/" + fileType
        if fileType == "Unmerged":
            base_path += "/*"

        # build filter string
        query = self._build_processed_query(
            seriesList, dataTypeList, beginDateTime, endDateTime
        )

        show = ["Series"]
        try:
            dataset_list = self.datasets.search(
                base_path, site=location, query=query, show=show
            )
        except Exception:
            print("ERROR: Problem accessing data catalog!")
            print(
                "Perhaps the files were produced prior January 2020 and do not "
                "have the proper metadata?"
            )
            return

        if not dataset_list:
            print(
                'WARNING: No processed file found for "'
                + productionTag
                + '". Check data catalog!'
            )
            return

        for dataset in dataset_list:
            series = dataset.metadata["Series"]
            file_name = dataset.filePath
            if outputSeriesDictFormat:
                output_dict.setdefault(series, []).append(file_name)
            else:
                output_list.append(file_name)

        return output_dict if outputSeriesDictFormat else output_list

    @staticmethod
    def _build_processed_query(
        seriesList, dataTypeList, beginDateTime, endDateTime
    ):
        """Build the datacat query string for processed-data search."""
        query = "nIsJunk==0"
        if seriesList:
            clauses = " or ".join(f'Series=="{s}"' for s in seriesList)
            query += f" and ({clauses})"
        if dataTypeList:
            clauses = " or ".join(f"nDataType=={d}" for d in dataTypeList)
            query += f" and ({clauses})"
        if beginDateTime:
            query += " and nSeriesDateTime>=" + str(beginDateTime)
        if endDateTime:
            query += " and nSeriesDateTime<=" + str(endDateTime)
        return query
