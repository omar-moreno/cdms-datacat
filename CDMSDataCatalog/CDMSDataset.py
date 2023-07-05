""" Provides the base CDMSDataset class as well as some derived ones"""
import os
from datacat.model import Metadata


class CDMSDataset:
    """Base class for CDMS datasets
    
    Attributes:
        datasetName (str): the `name` constructor argument
        filePath (str): path to file on disk, `None` if this object was
            retrieved from a catalog entry and not fetched
        dataType (str): facility where data was taken or sim type
        fileFormat (str): format of data file
        relativePath (str): The full data catalog entry path
        metadata (dict): additional metadata keys
        fetchError (str): If we attempted to fetch this data (i.e., find
            it on local disk or download it) and an error occurred, this
            will contain info on the error. Otherwise will be `None`
        size (int): size of data file in bytes
            
    """

    fileTypes = {'m': 'M', 'mat': 'CDMSMATLAB', 'root': 'CDMSROOT',
                 'txt': 'CDMSTXT', 'png': 'CDMSDMCPNG', 'epot': 'CDMSEPOT',
                 'supersim': 'CDMSHISTOGRAMS', 'midas': 'CDMSMIDAS',
                 'cdmsraw': 'CDMSSOUDANRAW', 'numpy': 'CDMSNUMPY',
                 'pickle': 'CDMSPICKLE', 'hdf5': 'CDMSHDF5',
                 'pmtroot': 'CDMSPMTROOT',
                 'error': 'ERROR', None:'ERROR'}

    """ List of allowed file types """
    
    fileFormats = {'m': 'm', 'mat': 'mat', 'root': 'root', 'txt': 'txt',
                   'epot': 'mat', 'supersim': 'root', 'png': 'png',
                   'pdf': 'pdf', 'midas': 'midas', 'cdmsraw': 'cdmsraw',
                   'numpy': 'npz', 'pickle': 'pickle','hdf5':'hdf5',
                   'pmtroot': 'root',
                   'error':None, None:None}
    """ List of allowed file formats (map type: suffix) """
    

    def __init__(self,
                 name,
                 filePath,
                 dataType,
                 site,
                 fileFormat):
        """ ##Constructor
        All arguments are mandatory; the optional metadata can be specified
        after construction.  This class should almost never be constructed
        directly.  `CDMSDataset`s constructed from data catalog entries
        retrieved through the web API will be built by the client using the
        `CDMSDataset.fromDataset` class function. To add new entries to the
        catalog, we will generally use subclasses tailored for that data type.

        Args:
            name (str): Name of the dataset entry. This should usually be the
                basename of the data file itself
            filePath (str): Full absolute path to the data file
            dataType (str): For raw/processed data, this is the facility
                where the data qas taken. Other data types may have different
                values here
            site (str): name of computing facility where the data is located
            fileFormat (str): descriptive name of format; key must be in
                `CDMSDataset.fileFormats`

       """
        self.datasetName = name
        self.filePath = filePath
        self.setDataType(dataType)
        self.setSite(site)
        self.setFileFormat(fileFormat)
        self.relativePath = '/CDMS/' + dataType if dataType else None
        self.metadata = Metadata()
        self.fetchError = None
        self.filesize = None 
        self.crcchecksum = None        

    @staticmethod
    def findLocation(rawds, site=None):
        """ Find the DatasetLocation for the specified site """
        location = None
        try:
            for loc in rawds.locations:
                if site == loc.site or site is None:
                    location = loc
                    break
            if location is None:
                location = rawds.locations[0]
        except (KeyError, AttributeError):
            pass
        return location

    @classmethod
    def fromDataset(cls, ds):
        """ Construct a `CDMSDataset` from a raw `datacat.model.Dataset` """
        site = None
        try:
            site = ds.site
        except AttributeError:
            location = cls.findLocation(ds)
            site = location.site

        nds = cls(str(ds.name), None,
                  dataType='DatacatQuery',
                  site=str(site),
                  fileFormat=str(ds.fileFormat))
        nds.relativePath = str(ds.path)
        
        # metadata may be called metadata or versionMetadata, so check both
        for metadata_name in ('metadata', 'versionMetadata'): 
            for k, v in getattr(ds, metadata_name, {}).items():
                nds.metadata[k] = v

        nds.rawDataset = ds
        return nds

    def _test_location_attr(self, attr, locationattr=None):
        """ Test for attributes in the raw dataset that may be attached to
            the SLAC location instead
        """
        result = None
        result = getattr(self.rawDataset, attr, None)
        if not result:
            location = self.findLocation(self.rawDataset, 'SLAC')
            if location:
                if not locationattr:
                    locationattr = attr
                result = getattr(location, locationattr, None)
        return result

    @property
    def locationPk(self):
        """Get the Pk of the first location from the raw dataset"""
        return self._test_location_attr('locationPk', 'pk')

    @property
    def size(self):
        """Get the file size (bytes) from the raw dataset"""
        return self._test_location_attr('size')

    def setFileFormat(self, fileFormat):
        """ Make sure `fileFormat` is one of the known types and set the
        corresponding member
        """
        try:
            self.fileFormat = CDMSDataset.fileFormats[fileFormat]
            self.fileType = CDMSDataset.fileTypes[fileFormat]
        except KeyError:
            raise ValueError('Unknown file format, known types are ' +
                             str(CDMSDataset.fileFormats.keys()))

    def setSite(self, site):
        self.site = site

    def setDataType(self, dataType):
        self.dataType = dataType

    def info(self):
        """Neatly output all information in dataset structure"""
        print("Name:        {}".format(self.datasetName))
        print("System Path: {}".format(self.filePath))
        print("Catalog Path:{}".format(self.relativePath))
        print("Site:        {}".format(self.site))
        print("Data Type:   {}".format(self.dataType))
        print("File Format: {}".format(self.fileFormat))
        print("File Type:   {}".format(self.fileType))
        print("Metadata:")
        for k, v in self.metadata.items():
            print("  - {0}: {1}".format(k, v))

    def getSitePaths(self):
        """ return a dict mapping site names to on-disk paths """
        locs = {}
        try:
            locs = {loc.site: loc.resource
                    for loc in self.rawDataset.locations}
        except AttributeError:
            pass
        if self.filePath:
            locs[self.site] = self.filePath
        return locs

    def __str__(self):
        return self.datasetName

    def __repr__(self):
        return '<CDMSDataset Class, Name: '+self.datasetName+'>'

    def keys(self):
        return self.metadata.keys()

    def __getitem__(self, key):
        return self.metadata[key]

    def __setitem__(self, key, value):
        self.metadata[key] = value


class DMCData(CDMSDataset):

    def __init__(self,
                 name,
                 filePath,
                 DMCType,
                 processStep='Postprocessed',
                 experiment='Soudan',
                 implement='MATLAB',
                 site='SLAC',
                 fileFormat='root',
                 analysis='All',
                 analysisVersion='53',
                 detector='All',
                 DMCVersion='5-3',
                 COMSOLVersion='5.0'):
        """Constructor for the CDMS DMC dataset class

        All of these are mandatory; the optional metadata can be specified
        after construction

        name     - dataset name
        filePath - physical path to file
        DMCType  - 'Cf','Ba','WIMP',...

        Optional Inputs
        experiment  - 'Soudan' (default), 'SNOLAB', 'TestDevices'
        implement   - 'MATLAB' (default), 'Geant'
        processStep - 'Constants', 'SuperSim', 'Raw', 'Preprocessed',
                      'Postprocessed' (default)
        site        - e.g. 'SLAC' (default)
        fileFormat  - 'root' (default), 'mat', 'txt'
        analysis    - e.g. 'All' (default), 'HT', 'LT', 'G133'
        analysisVersion - e.g. '53' (default)
        detector    - e.g. 'All' (default), 'T1Z1'
        DMCVersion  - e.g. '5-3' (default)
        COMSOLVersion - e.g. 5.0 (default)
        """
        CDMSDataset.__init__(self, name, filePath, experiment + '/DMC', site,
                             fileFormat)

        processSteps = ['Constants', 'SuperSim', 'Raw', 'Preprocessed',
                        'Postprocessed']
        if(processStep in processSteps):
            self.processStep = processStep
        else:
            raise ValueError("Please specify DMC process level (processStep),"
                             " options are " + str(processSteps))

        # add implementation to path
        self.implement = implement
        self.relativePath += '/' + self.implement

        # add analysis and source to path
        self.relativePath += '/'+analysis + '/'+DMCType

        # add category to path
        if(self.processStep in ['Constants', 'SuperSim']):
            self.relativePath += '/Input/' + self.processStep
        elif(self.processStep in ['Raw', 'Preprocessed', 'Postprocessed']):
            self.relativePath += '/Production/' + self.processStep

        # add detector if necessary
        if(self.processStep in ['Constants', 'Raw', 'Preprocessed']):
            self.relativePath += '/' + detector

        self.metadata["Analysis"] = analysis
        self.metadata["AnalysisVersion"] = analysisVersion
        self.metadata["COMSOLVersion"] = COMSOLVersion
        self.metadata["Detector"] = detector
        self.metadata["DMCImpl"] = implement
        self.metadata["DMCversion"] = DMCVersion
        self.metadata["Source"] = DMCType
        self.metadata["SourceLoc"] = 'None'
        self.metadata["EnergyMax"] = '-1'
        self.metadata["EnergyMin"] = '-1'
        self.metadata["NoiseProfile"] = 'NA'
        self.metadata["WIMPmass"] = "-1"
        

class ProdSimDataset(CDMSDataset):

    def __init__(self,
                 filename, filePath, dataType, site, fileFormat, # Required by constructor of CDMSDataset base class
                 OfflineRelease, Series, SimStage, Source, DetType, EnergyDeposit, nEvAll,
                 FridgeRun = None, MCSetup = None, MCType = None, MCVersion = None, # Used to assign folder in Data Catalog
                 Ancestorpath = None): # Predecessor information
        """Constructor for the CDMS DMCintermediate dataset class
        filename         - Dataset name
        filePath         - Full path to actual file, including file name
        dataType         - Required values: 'ANIMAL', 'CUTE', 'NEXUS', 'NoLab', 'SLAC', 'SNOLAB', 'Soudan', 'TRIUMF', 'UCB', 'UMN'
        site             - For example, 'SLAC'
        fileFormat       - For example, 'root' or 'txt'
        """ 
        CDMSDataset.__init__(self, filename, filePath, dataType, site, fileFormat)
        self.metadata_folder = Metadata()
        self.path_is_valid = False
        self.relativePath = self.relativePath.replace('/CDMS/', '/CDMS/Test2/test_dc3/') # For testing purposes only

        if type(FridgeRun) == str and MCSetup == None and MCType == None and MCVersion == None:
            self.metadata['FridgeRun'] = FridgeRun
            self.metadata_folder['FridgeRun'] = FridgeRun
            self.relativePath += '/'+FridgeRun+'/Simulated'
            self.path_is_valid = True
        elif FridgeRun == None and type(MCSetup) == str and type(MCType) == str and type(MCVersion) == str:
            if len(MCSetup) > 0 and len(MCType) > 0 and len(MCVersion) > 0:
                ProdTag = '_'.join([MCSetup, MCType, MCVersion])
                self.metadata['ProdTag'] = ProdTag
                self.metadata_folder['ProdTag'] = ProdTag
                self.relativePath += '/'+ProdTag+'/Simulated'
                self.path_is_valid = True
        if not self.path_is_valid:
            print('ERROR: FridgeRun and ProdTag are undefined, will be required to build folder path')
        self.relativePath_common = self.relativePath

        self.metadata['Series'       ] = Series
        self.metadata['Source'       ] = Source
        self.metadata['DetType'      ] = DetType
        self.metadata['EnergyDeposit'] = EnergyDeposit
        self.metadata['nEvAll'       ] = nEvAll

        self.metadata_folder['OfflineRelease'] = OfflineRelease
        self.metadata_folder['SimStage'      ] = SimStage
        self.metadata_folder['Source'        ] = Source
        self.metadata_folder['Facility'      ] = dataType
        self.metadata_folder['DetType'       ] = DetType
        self.metadata_folder['EnergyDeposit' ] = EnergyDeposit

        self.required_values = {} # To be also filled in the constructor of each specific class, if necessary
        self.required_values['SimStage'] = ['SourceSim',
                                            'DMC'      ,
                                            'DAQSim'   ,
                                            'CDMSBats' ]
        self.required_values['Facility'] = ['ANIMAL',
                                            'CUTE'  ,
                                            'NEXUS' ,
                                            'NoLab' ,
                                            'SLAC'  ,
                                            'SNOLAB',
                                            'Soudan',
                                            'TRIUMF',
                                            'UCB'   ,
                                            'UMN'   ]
        self.required_values['Source'] = ['Am241',
                                          'Ba133',
                                          'Cf252',
                                          'DMCER',
                                          'DMCNR',
                                          'Ge71' ,
                                          'Si32' ,
                                          'Pb210',
                                          'Radon',
                                          'WIMP' ,
                                          'SbBe' ,
                                          'YBe'  ]

        self.Ancestorpath = Ancestorpath

    def check_conventions(self): # To be called before registering
        if not self.path_is_valid: # Check that folder path has the correct format
            print('ERROR: unable to build valid folder path with the metadata provided')
            return False

        print('Dataset metadata:')
        max_len_param = max([len(parameter) for parameter in self.metadata.keys()])
        for parameter in self.metadata.keys(): # Check that metadata take allowed values
            if parameter in self.required_values.keys():
                if not self.metadata[parameter] in self.required_values[parameter]:
                    print('ERROR: metadata field', parameter, 'does not take any of the allowed values')
                    print('Allowed values are:', ', '.join(self.required_values[parameter]))
                    return False

            if parameter[0] == 'n' and parameter[1].isupper():
                try:
                    self.metadata[parameter] = int(self.metadata[parameter])
                except:
                    print('ERROR: unable to convert metadata field', parameter, 'to int')
                    return False
            else:
                self.metadata[parameter] = str(self.metadata[parameter])
                
            print('-', parameter.ljust(max_len_param), self.metadata[parameter])

        print('Folder metadata:')
        max_len_param = max([len(parameter) for parameter in self.metadata_folder.keys()])
        for parameter in self.metadata_folder.keys(): # Check that metadata take allowed values
            if parameter in self.required_values.keys():
                if not self.metadata_folder[parameter] in self.required_values[parameter]:
                    print('ERROR: metadata field', parameter, 'does not take any of the allowed values')
                    print('Allowed values are:', ', '.join(self.required_values[parameter]))
                    return False

            if parameter[0] == 'n' and parameter[1].isupper():
                try:
                    self.metadata_folder[parameter] = int(self.metadata_folder[parameter])
                except:
                    print('ERROR: unable to convert metadata field', parameter, 'to int')
                    return False
            else:
                self.metadata_folder[parameter] = str(self.metadata_folder[parameter])
                
            print('-', parameter.ljust(max_len_param), self.metadata_folder[parameter])

        return True

    def get_ancestors(self, dc_default):
        try:
            return dc_default.search(self.relativePath_common+'/**', query = 'resource eq "'+self.Ancestorpath+'"')
        except:
            return None


class ParticleHits(ProdSimDataset):

    def __init__(self,
                 filename, filePath, site, fileFormat,
                 OfflineRelease, Series, SimStage, Source, Facility, DetType, EnergyDeposit, nEvAll,
                 FridgeRun = None, MCSetup = None, MCType = None, MCVersion = None):
        ProdSimDataset.__init__(self,
                                filename, filePath, Facility, site, fileFormat,
                                OfflineRelease, Series, SimStage, Source, DetType, EnergyDeposit, nEvAll,
                                FridgeRun, MCSetup, MCType, MCVersion)
        self.relativePath += '/SourceSim/V'+self.metadata_folder['OfflineRelease']


class DMCintermediate(ProdSimDataset):

    def __init__(self,
                 filename, filePath, site, fileFormat,
                 OfflineRelease, Series, SimStage, Source, Facility, DetType, EnergyDeposit, nEvAll,
                 FridgeRun = None, MCSetup = None, MCType = None, MCVersion = None,
                 Ancestorpath = None):
        ProdSimDataset.__init__(self,
                                filename, filePath, Facility, site, fileFormat,
                                OfflineRelease, Series, SimStage, Source, DetType, EnergyDeposit, nEvAll,
                                FridgeRun, MCSetup, MCType, MCVersion,
                                Ancestorpath)
        self.relativePath += '/DMC/V'+self.metadata_folder['OfflineRelease']


class RawSim(ProdSimDataset):

    def __init__(self,
                 filename, filePath, site, fileFormat,
                 OfflineRelease, Series, SimStage, Source, Facility, DetType, EnergyDeposit, nEvAll,
                 IOLibrary, BatCommon, nAddNoise,
                 nDataType, nDumps, nDump, nEvBORR, nFirstTriggerId, nLastTriggerId,
                 FridgeRun = None, MCSetup = None, MCType = None, MCVersion = None,
                 Ancestorpath = None):
        ProdSimDataset.__init__(self,
                                filename, filePath, Facility, site, fileFormat,
                                OfflineRelease, Series, SimStage, Source, DetType, EnergyDeposit, nEvAll,
                                FridgeRun, MCSetup, MCType, MCVersion,
                                Ancestorpath)
        self.relativePath += '/DAQSim/V'+self.metadata_folder['OfflineRelease']

        self.metadata['nDataType'      ] = nDataType
        self.metadata['nDump'          ] = nDump
        self.metadata['nEvBORR'        ] = nEvBORR
        self.metadata['nFirstTriggerId'] = nFirstTriggerId
        self.metadata['nLastTriggerId' ] = nLastTriggerId

        self.metadata_folder['IOLibrary'] = IOLibrary
        self.metadata_folder['BatCommon'] = BatCommon
        self.metadata_folder['nAddNoise'] = nAddNoise
        self.metadata_folder['nDataType'] = nDataType
        self.metadata_folder['nDumps'   ] = nDumps

        self.required_values['nDataType'] = ['200']

class ProcessedSim(ProdSimDataset):

    def __init__(self,
                 filename, filePath, site, fileFormat,
                 OfflineRelease, Series, SimStage, Source, Facility, DetType, EnergyDeposit, nEvAll,
                 IOLibrary, BatCommon,
                 nDataType, nDump, nEvBORR,
                 ProcessingConfig, CalibAnalysisConfig, CalibProcessingConfig, AnalysisConfig,
                 CdmsBats, CdmsBatsSettings, CdmsBatsPath, CdmsBatsSettingsPath, nIsCdmsBatsProd, nIsCdmsBatsSettingsProd,
                 FridgeRun = None, MCSetup = None, MCType = None, MCVersion = None,
                 Ancestorpath = None):
        ProdSimDataset.__init__(self,
                                filename, filePath, Facility, site, fileFormat,
                                OfflineRelease, Series, SimStage, Source, DetType, EnergyDeposit, nEvAll,
                                FridgeRun, MCSetup, MCType, MCVersion,
                                Ancestorpath)
        self.relativePath += '/Processed/V'+self.metadata_folder['OfflineRelease']+'_P'+ProcessingConfig

        self.metadata['nDataType'            ] = nDataType
        self.metadata['nDump'                ] = nDump
        self.metadata['nEvBORR'              ] = nEvBORR
        self.metadata['ProcessingConfig'     ] = ProcessingConfig
        self.metadata['CalibAnalysisConfig'  ] = CalibAnalysisConfig
        self.metadata['CalibProcessingConfig'] = CalibProcessingConfig
        self.metadata['AnalysisConfig'       ] = AnalysisConfig

        self.metadata_folder['IOLibrary'              ] = IOLibrary
        self.metadata_folder['BatCommon'              ] = BatCommon
        self.metadata_folder['nDataType'              ] = nDataType
        self.metadata_folder['ProcessingConfig'       ] = ProcessingConfig
        self.metadata_folder['CalibAnalysisConfig'    ] = CalibAnalysisConfig
        self.metadata_folder['CalibProcessingConfig'  ] = CalibProcessingConfig
        self.metadata_folder['AnalysisConfig'         ] = AnalysisConfig
        self.metadata_folder['CdmsBats'               ] = CdmsBats
        self.metadata_folder['CdmsBatsSettings'       ] = CdmsBatsSettings
        self.metadata_folder['CdmsBatsPath'           ] = CdmsBatsPath
        self.metadata_folder['CdmsBatsSettingsPath'   ] = CdmsBatsSettingsPath
        self.metadata_folder['nIsCdmsBatsProd'        ] = nIsCdmsBatsProd
        self.metadata_folder['nIsCdmsBatsSettingsProd'] = nIsCdmsBatsSettingsProd

        self.required_values['nDataType'] = ['200']


class SuperSimData(CDMSDataset):

    def __init__(self,
                 name,
                 filePath,
                 SuperSimType,
                 SuperSimVersion,
                 experiment='Soudan',
                 site='SLAC',
                 fileFormat='root'):
        """Constructor for the CDMS SuperSim dataset class

        All of these are mandatory; the optional metadata can be specified
        after construction

        name     - dataset name
        filePath - physical path to file
        SuperSimType  - e.g. 'Backgrounds'
        SuperSimVersion - e.g. 1.0

        Optional Inputs
        experiment  - 'Soudan' (default), 'SNOLAB', 'TestDevices', 'UMN', 'UCB'
        site        - e.g. 'SLAC' (default)
        fileFormat  - 'root' (default), 'mat', 'txt'
        SuperSimVersion - e.g. 1.0 (default)
        """
        CDMSDataset.__init__(self, name, filePath, experiment + '/SuperSim',
                             site, fileFormat)

        # add simulation type to path
        self.relativePath += '/' + SuperSimType + '/' + SuperSimVersion

        self.metadata["SuperSimType"] = SuperSimType
        self.metadata["SuperSimVersion"] = SuperSimVersion 


class RawData(CDMSDataset):

    def __init__(self,
                 fileName,
                 filePath,
                 facility,
                 nFridgeRun,
                 nDataType,
                 series,
                 nDump,
                 nEventsAll,
                 nEventsBORR,
                 nEventsEORR,
                 nEventsBORTS,
                 nEventsEORTS,
                 nIsJunk,
                 dataLocation='SLAC',
                 fileFormat='midas',
                 commentStart='None',
                 commentEnd='None',
                 nFirstTriggerId=-1,
                 nLastTriggerId=-1,
                 fileSize = None,
                 checksum = None):
        '''
        Constructor for the CDMS RawData dataset class
        '''

        # instantiate CDMSDataset base object
        CDMSDataset.__init__(self, fileName, filePath,
                             facility, dataLocation, fileFormat)
        self.relativePath += '/R'+str(nFridgeRun)+'/Raw/'+str(series)

        self.metadata["Facility"] = facility
        self.metadata["nFridgeRun"] = int(nFridgeRun)
        self.metadata["nDataType"] = int(nDataType)
        self.metadata["Series"] = series
        if nDump is not None: self.metadata["nDump"] = int(nDump)
        self.metadata["nEvAll"] = int(nEventsAll)
        self.metadata["nEvBORR"] = int(nEventsBORR)
        self.metadata["nEvEORR"] = int(nEventsEORR)
        self.metadata["nEvBORTS"] = int(nEventsBORTS)
        self.metadata["nEvEORTS"] = int(nEventsEORTS)
        self.metadata["CommentStart"] = commentStart
        self.metadata["CommentEnd"] = commentEnd
        self.metadata["nIsJunk"] = int(nIsJunk)
        self.metadata["nFirstTriggerId"] = int(nFirstTriggerId)
        self.metadata["nLastTriggerId"] = int(nLastTriggerId)

        if fileSize is not None:
            self.filesize = fileSize
        if checksum is not None:
            self.crcchecksum = checksum

        

class ContinuousRawData(CDMSDataset):

    def __init__(self,
        fileName,
        filePath,
        facility,
        nFridgeRun,
        nDataType,
        series,
        nIsJunk,
        dataLocation = 'SLAC',
        fileFormat = 'hdf5',
        commentStart = 'None',
        commentEnd = 'None',
        nDumpNum = None):
		
        '''
        Constructor for raw data taken with continuous DAQ
	    '''

        #Instantiate CDMSDataset Base Object
        CDMSDataset.__init__(self, fileName, filePath, facility, dataLocation, fileFormat)
        
        self.relativePath += '/R' + str(nFridgeRun) + '/Raw/' + str(series)
        self.metadata["nFridgeRun"] = int(nFridgeRun)
        self.metadata["nDataType"] = int(nDataType)
        self.metadata["Series"] = series
        self.metadata["nIsJunk"] = int(nIsJunk)
        self.metadata["CommentStart"] = commentStart
        self.metadata["CommentEnd"] = commentEnd
        if nDumpNum is not None:
            self.metadata["nDump"] = int(nDumpNum)

class ProcessedData(CDMSDataset):

    def __init__(self,
                 fileName, 
                 filePath,
                 datacatPath,
                 facility,
                 nFridgeRun,
                 nDataType,
                 series,
                 prodStep,
                 prodTag='Test',
                 prodType='test',
                 nMergeLevel = 0,
                 dataLocation='SLAC',
                 fileFormat='root',
                 commentStart = 'None',
                 commentEnd = 'None',
                 nIsJunk=0,
                 nDump = 0,
                 noiseDumps = '0',
                 processing_config = 'None',
                 analysis_config = 'None',
                 calib_processing_config = 'None',
                 calibration_config = 'None',
                 nEventsAll = 0,
                 nEventsBORR = 0,
                 nEventsEORR=0,
                 nEventsBORTS=0,
                 nEventsEORTS=0,
                 analysis = 'All',
                 cutName ='cGood',
                 cutVersion ='0'):
        
        """
        Constructor for the CDMS processed dataset class
        """
        # Some checks
        prodSteps=['BatNoise','BatRoot','BatCalib','Cut', 'PyNoise', 'PyTemplate', 'PyPkl', 'PyPklRRQ']
        if(not prodStep in prodSteps):
                raise ValueError("Please specify data process level (prodStep), options are "+str(prodSteps))
 

        # instantiate CDMSDataset base object
        CDMSDataset.__init__(self,fileName,filePath,facility,dataLocation,fileFormat)
        self.relativePath = datacatPath
      
        #add category to path
        if (prodStep == 'BatNoise') or (prodStep == 'PyNoise'):
            self.relativePath+='/Noise'
        elif (prodStep == 'Cut'):
            self.relativePath+='/Cuts'
        else:
            if int(nMergeLevel)==0:
                self.relativePath+='/Unmerged/' + series
            elif int(nMergeLevel)==1:
                self.relativePath+='/Submerged'
            elif int(nMergeLevel)==2:
                self.relativePath+='/Merged'
            
                
        # series data time
        # remove underscore and facility ID (first 2 digit)
        pos_underscore = series.find('_')
        series_time = series[pos_underscore-6:]
        series_time =  series_time.replace('_','')
        if len(series_time)==10:
            series_time += '00'


        # metadata
        self.metadata["Facility"]=facility
        self.metadata["nFridgeRun"]=int(nFridgeRun)
        self.metadata["nDataType"]=int(nDataType)
        self.metadata["nSeriesDateTime"]=int(series_time)
        self.metadata["Series"]=series
        self.metadata["CommentStart"] = commentStart
        self.metadata["CommentEnd"] = commentEnd
        self.metadata["nIsJunk"]=int(nIsJunk)
        self.metadata["ProdStep"] = prodStep
        self.metadata["ProdTag"] = prodTag
        self.metadata["ProdType"] = prodType
        self.metadata["nMergeLevel"] = int(nMergeLevel)
        if prodStep=='BatNoise':
            self.metadata["DumpsNoise"] = str(noiseDumps)
                  
        if prodStep=='BatRoot' or prodStep=='BatCalib':
            self.metadata["nEvAll"]=int(nEventsAll)
            self.metadata["nEvBORR"] = int(nEventsBORR)
            self.metadata["nEvEORR"] = int(nEventsEORR)
            self.metadata["nEvBORTS"] =int(nEventsBORTS)
            self.metadata["nEvEORTS"] = int(nEventsEORTS)
               
            if int(nMergeLevel)==0:
                self.metadata["nDump"] = int(nDump)
            else:
                self.metadata["Dumps"]=str(nDump)
                

        self.metadata["ProcessingConfig"] = processing_config
        self.metadata["AnalysisConfig"] = analysis_config
      
        if prodStep=='BatCalib':
            self.metadata["CalibProcessingConfig"] = calib_processing_config
            self.metadata["CalibAnalysisConfig"] = calibration_config
        


        if prodStep=='Cut':
            self.metadata["Analysis"] = analysis
            self.metadata["CutName"] = cutName
            self.metadata["CutVersion"] = CutVersion



class ProcessedIVdIdVData(CDMSDataset):

    def __init__(self,
                 fileName,
                 filePath,
                 facility,
                 nFridgeRun,
                 nDataType,
                 series,
                 prodType,
                 nStep,
                 nTotalSteps,
                 prodVersion='Test',
                 dataLocation='SLAC',
                 fileFormat='pickle',
                 commentStart='None',
                 commentEnd='None',
                 nIsJunk=0):

        """
        Constructor for the CDMS processed dataset class
        """
        # Some checks
        prodTypes = ['IV', 'dIdV']
        if(prodType not in prodTypes):
            raise ValueError("Please specify data process level (prodStep), "
                             "options are "+str(prodTypes))

        # instantiate CDMSDataset base object
        CDMSDataset.__init__(self, fileName, filePath, facility, dataLocation,
                             fileFormat)

        # Build Data catalog path
        self.relativePath += ('/R' + str(nFridgeRun) +
                              '/Processed/IV_dIdV_Sweeps/' + prodVersion)

        # metadata
        self.metadata["Facility"] = facility
        self.metadata["nFridgeRun"] = int(nFridgeRun)
        self.metadata["nDataType"] = int(nDataType)
        self.metadata["Series"] = series
        self.metadata["CommentStart"] = commentStart
        self.metadata["CommentEnd"] = commentEnd
        self.metadata["nIsJunk"] = int(nIsJunk)
        self.metadata["ProdType"] = prodType
        self.metadata["nStep"] = int(nStep)
        self.metadata["nTotalSteps"] = int(nTotalSteps)
        self.metadata["ProdVersion"] = prodVersion

class MidasToolsData(CDMSDataset):

    def __init__(self,
                 fileName,
                 filePath,
                 facility,
                 nFridgeRun,
                 series,
                 devices,
                 tests,
                 comment,
                 dataLocation='SLAC',
                 fileFormat='root',
                 nIsJunk=0):

        """
        Constructor for the CDMS MidasTools dataset class
        """

        # instantiate CDMSDataset base object
        CDMSDataset.__init__(self, fileName, filePath, facility, dataLocation,
                             fileFormat)

        # Build Data catalog path
        self.relativePath += ('/R' + str(nFridgeRun) + '/MidasTools')

        # metadata
        self.metadata["Facility"] = facility
        self.metadata["nFridgeRun"] = int(nFridgeRun)
        self.metadata["Series"] = series
        self.metadata["Devices"] = devices
        self.metadata["Tests"] = tests
        self.metadata["Comment"] = comment
        self.metadata["nIsJunk"] = int(nIsJunk)
