import datacat
from datacat import client_from_config_file
from datacat.model import Metadata
import pathlib
from multiprocessing.pool import ThreadPool
import urllib
import shutil
import os
import requests

def corrPathCDMS(path):
    if(path[0] != '/'):
        path="/"+path
        
    if(path[1:5] != "CDMS"):
        path="/CDMS"+path
        
    return path

def getFileFormat(filePath):
    return ''.join(pathlib.Path(filePath).suffixes).strip('.')

class CDMSFetchResult(object):
    """An instance of this class is returned by `fetch` operations. 
    It is truthy if all fetches completed successfully. Details on each 
    individual request are provided.
    """
    
    def __init__(self, request, success, filePath=None, error=None):
        self.request = request
        self.filePath = filePath
        self.success = success
        self.error = error
        #if not success:
        #    self.summary()
        
    def summary(self):
        if self.success:
            print("Fetch",self.request,"succeeded. File at",self.filePath)
        else:
            print("\x1b[1;31mFetch",self.request,"failed:\x1b[0m",self.error)
            
    def __bool__(self):
        return self.success

    def __repr__(self):
        return "CDMSFetchRequest(%s)"%("success" if self.success else "failed")
        
    def __str__(self):
        return repr(self)

class CDMSMultiFetchResult(CDMSFetchResult):
    """Container for multiple fetch requests"""
    def __init__(self, results):
        self.request = results
        self.filePath = None

    def summary(self):
        if self.success:
            print("All", len(self.request), "fetches succeeded")
        else:
            succeeded = sum(1 for req in self.request if req)
            print(succeeded, "out of", len(self.request), "succeeded")
            for req in self.request:
                req.summary()

    def __getitem__(self, key):
        return self.request[key]

    def __iter__(self):
        return self.request.__iter__()
        
    @property
    def success(self):
        return all(self.request)
    
    @success.setter
    def success(self, val):
        pass

    @property
    def error(self):
        return {res.request: res.error for res in self.request if not res}

    @error.setter
    def error(self, val):
        pass
    

class CDMSDataCatalog:
    
    def __init__(self,config_file=None):
        self.client = client_from_config_file(config_file) if config_file else client_from_config_file()
        #todo: get default location from config file
        self.defaultDataRoot = 'datacat_data'
        
    def ls(self,path='/CDMS/'):
        """ Return contents of a datacat path, by default look in /CDMS/ """
        path=corrPathCDMS(path)
        try:
            for child in self.client.children(path):
                print(child.path)
        except TypeError:
            print("Cannot ls, %s is a dataset" % path)
        except:
            print("Path does not exist")

    def exist(self,path,versionId=None,site=None):
        path=corrPathCDMS(path)
        do_exist = self.client.exists(path, versionId, site)
        return do_exist

    def rm(self,path,recursive=False,verbose=True):
        path=corrPathCDMS(path)
        
        if(verbose):
            print(path)
        if(recursive):
            try:
                if(type(self.client.path(path)) == datacat.model.Dataset):
                    self.client.rmds(path)
                    return
            except Exception as e:
                print("Couldn't delete %s" % path)
                return

            else:
                for child in self.client.children(path):
                    self.rm(child.path,recursive=True)

                ctype='folder'
                if(type(self.client.path(path)) == datacat.model.Group):
                    ctype='group'
                
                if(verbose):
                    print(path)
                try:
                    self.client.rmdir(path,type=ctype)
                except Exception as e:
                    print("Couldn't delete %s" % path)
                return
        else:
            try:
                if(type(self.client.path(path)) == datacat.model.Dataset):
                    self.client.rmds(path)
                else:
                    self.client.rmdir(path)
            except Exception as e:
                print(e)
                raise IOError("Couldn't delete "+path)

    def mkdir(self,path,parents=False):
        path=corrPathCDMS(path)
        self.client.mkdir(path,parents=parents)
        return

    def search(self,path,*args, **kwargs):
        path=corrPathCDMS(path)
        results=self.client.search(path,*args, **kwargs)
        #results come back unsorted, which is not what we want
        results.sort(key=lambda res: res.path)
        return list(CDMSDataset.fromSearchDataset(res) for res in results)

    def get(self,path,site='All'):
        path=corrPathCDMS(path)
        return CDMSDataset.fromDataset(self.client.path(path,site=site))

    def fetch(self, path, dest=None, destRelative=True, force=False,
              maxthreads=None):
        """Download a copy of the files pointed by path to the local system. 
        Args:
          path:  The file(s) to copy. Can take many forms:
                 - a single string giving the full data catalog entry path
                 - a CDMSDataset
                 - a CDMSDataGroup (or path pointing to): download all ref'd
                 - a list/tuple of paths/Datasets

          dest (str or Path): target directory to place the file in. 
                              Missing directories will be created. File
                              will have same name as data catalog entry
          destRelative (bool): If True (default), create a directory 
                               hierarchy under `destimation` to match
                               the `relativePath` member. If `path` has
                               multiple entries, will be treated as True
          force (bool): If True, overwrite an existing file at the destination.
                        If False (default), return failure if existing file
                        doesn't match datacat entry. 
          maxthreads (int): If a list, use up to `maxthreads` simultaneous
                            download connections
        Returns:
          CDMSFetchResult: If file was successfully downloaded / already exists
                          and passes size or checksum verification, return True.
                          Also update the `filePath` member to the new location.
                          Else returns False, though in many cases an exception
                          will be raised first.
        """
        #check destination
        if dest is None:
            dest = self.defaultDataRoot
        
        #first check the type of path
        if isinstance(path, (list, tuple)):
            #fetch each one individually (in multiple threads), return the set
            if maxthreads is not None:
                maxthreads = min(maxthreads, len(path))
            with ThreadPool(processes=maxthreads) as pool:
                def dofetch(apath):
                    return self.fetch(apath, dest, destRelative, force)
                return CDMSMultiFetchResult(pool.map(dofetch, path))
        
        elif isinstance(path,str):
            #convert to a Dataset
            try:
                path = self.get(path)
            except BaseException as e:
                return CDMSFetchResult(path, success=False, error=str(e))

        #if we get here, path _should_ be a CDMSDataset
        dataset = path
        if not isinstance(dataset, CDMSDataset):
            error="Unhandled type '{}' for `path` argument".format(type(path))
            return CDMSFetchResult(path, success=False, error=error)

        #need low-level dataset items later
        rawds = getattr(dataset, 'rawDataset', None)
        filesize = getattr(rawds,'size',rawds.locations[0].size)
            
        #figure out the full destination path/filename
        target = dest
        if destRelative:
            relPath = dataset.relativePath
            if os.path.isabs(relPath):
                relPath = relPath[1:]
            target = os.path.join(target, relPath)
        else:
            target = os.path.join(target, dataset.datasetName)
        
        targetexists = os.path.isfile(target)
        if force or not targetexists:
            #we need to actually do the download
            targetDir = os.path.dirname(target)
            try:
                pathlib.Path(targetDir).mkdir(parents=True, exist_ok=True)
            except BaseException as e:
                error = "Unable to create target directory {}: {}"
                error = error.format(targetDir, e)
                return CDMSFetchResult(path, success=False, error=error)

            #determine the URL for the file
            baseparsed = urllib.parse.urlparse(self.client.http_client.base_url)
            url = urllib.parse.urlunparse((baseparsed[0], baseparsed[1],
                                           'DataCatalog/get','','',''))
            #need to get raw dataset to determine url
            locationPk = dataset.locationPk
            if locationPk is None:
               return CDMSFetchResult(path, success=False, 
                                      error="Unable to generate download URL") 
            params = dict(datasetLocation=locationPk)
            #finally we can download to file
            #from https://stackoverflow.com/questions/16694907/
            mb = dataset.size/1024/1024 if dataset.size else "unknown"
            print("Downloading file", dataset.datasetName, "%.2f"%mb,"MB")
            #what about auth?
            with requests.get(url, params=params, stream=True) as req:
                with open(target, 'wb') as f:
                    shutil.copyfileobj(req.raw, f)
            print("Finished downloading",dataset.datasetName)
            
        #now make sure the local file matches size
        try:
            size = os.path.getsize(target)
        except OSError as e:
            return CDMSFetchResult(path, success=False, filePath=target,
                                   error="File not downloaded: {}".format(e))
        if dataset.size is not None and size != dataset.size:
            return CDMSFetchResult(path, success=False, filePath=target,
                                   error="File size does not match")

        #finally we are successful!
        return CDMSFetchResult(path, success=True, filePath=target)
        

    def add(self,CDMSds,replace=True,catch_errors=True):
        if(CDMSds.dataType == 'DatacatQuery'):
            raise ValueError('Cannot commit dataset with type "DatacatQuery", invalid type')
        try:
            path=corrPathCDMS(CDMSds.relativePath)
            if(not self.client.exists(path)):
                self.mkdir(path,parents=True)
            DSexists = self.client.exists(path+'/'+CDMSds.datasetName)
            if(DSexists):
                if(replace):
                    print('Replacing existing dataset: {0}/{1}'.format(path, CDMSds.datasetName))
                    self.rm(path+'/'+CDMSds.datasetName)
                else:
                    print('Skipping existing dataset: {0}/{1}'.format(path, CDMSds.datasetName))

            if(not DSexists or replace):
                self.client.mkds(path,
                                 CDMSds.datasetName,
                                 CDMSds.fileType,
                                 CDMSds.fileFormat,
                                 versionMetadata=CDMSds.metadata,
                                 resource=CDMSds.filePath,
                                 site=CDMSds.site)
        except Exception as e:
            if catch_errors:
                print(e)
                print("Could not create dataset")
            else:
                raise
                 
class CDMSDataset:
    """Base class for CDMS datasets"""
    
    fileTypes={'m':'M','mat':'CDMSMATLAB','root':'CDMSROOT','txt':'CDMSTXT','png':'CDMSDMCPNG','epot':'CDMSEPOT','supersim':'CDMSHISTOGRAMS','midas':'CDMSMIDAS','cdmsraw':'CDMSSOUDANRAW','numpy':'CDMSNUMPY'}
    fileFormats={'m':'m','mat':'mat','root':'root','txt':'txt','epot':'mat','supersim':'root','png':'png','pdf':'pdf','midas':'midas','cdmsraw':'cdmsraw','numpy':'npz'}
    
    def __init__(self,
                 name, 
                 filePath,
                 dataType,
                 site,
                 fileFormat):
        """Constructor for the CDMS dataset base class
        
        All of these are mandatory; the optional metadata can be specified after construction
        name - dataset name
        filePath - physical path to file
        dataType/Facility- 'DMC', 'Soudan', 'SNOLAB', 'UCB', etc
        site -  e.g. 'SLAC'
        fileFormat - e.g. 'root', 'mat', 'txt', 'm', 'epot','midas'
        
        """
        self.datasetName=name
        self.filePath=filePath
        self.setDataType(dataType)
        self.setSite(site)
        self.setFileFormat(fileFormat)
        self.relativePath='/CDMS/'+self.dataType
        self.metadata = Metadata()

    @classmethod
    def fromDataset(cls,ds):
        print(ds.resource)
        nds = cls(str(ds.name),str(ds.resource),
                  dataType='DatacatQuery',
                  site=str(ds.site),
                  fileFormat=str(ds.fileFormat))
        nds.relativePath=str(ds.path)
        for k,v in ds.versionMetadata.items():
            nds.metadata[k]=v
        nds.rawDataset = ds
        return nds

    @classmethod
    def fromSearchDataset(cls,ds):
        nds = cls(str(ds.name),str(ds.locations[0].resource),
                  dataType='DatacatQuery',
                  site=str(ds.locations[0].site),
                  fileFormat=str(ds.fileFormat))
        nds.relativePath=str(ds.path)
        if hasattr(ds,'metadata'):
            for key,value in ds.metadata.items():
                nds.metadata[key]=value
        nds.rawDataset = ds
        return nds

    @property
    def locationPk(self):
        """Get the Pk of the first location from the raw dataset"""
        try:
            return getattr(self.rawDataset, 'locationPk', 
                           self.rawDataset.locations[0].pk)
        except:
            return None
    
    @property
    def size(self):
        """Get the file size from the raw dataset"""
        try:
            return getattr(self.rawDataset, 'size', 
                           self.rawDataset.locations[0].size)
        except:
            return None

    def setFileFormat(self,fileFormat):
        try:
            self.fileFormat=CDMSDataset.fileFormats[fileFormat]
            self.fileType=CDMSDataset.fileTypes[fileFormat]
        except KeyError:
            raise ValueError('Unknown file format, known types are '+str(CDMSDataset.fileFormats.keys()))

    def setSite(self,site):
        self.site=site

    def setDataType(self,dataType):
        self.dataType=dataType
    
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
        for k,v in self.metadata.items():
            print("  - {0}: {1}".format(k,v))

    def __str__(self):
        return self.datasetName

    def __repr__(self):
        return '<CDMSDataset Class, Name: '+self.datasetName+'>'

    def keys(self):
        return self.metadata.keys()

    def __getitem__(self,key):
        return self.metadata[key]

    def __setitem__(self,key,value):
        self.metadata[key]=value

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
        
        All of these are mandatory; the optional metadata can be specified after construction
        name     - dataset name
        filePath - physical path to file
        DMCType  - 'Cf','Ba','WIMP',...

        Optional Inputs
        experiment  - 'Soudan' (default), 'SNOLAB', 'TestDevices'
        implement   - 'MATLAB' (default), 'Geant'
        processStep - 'Constants', 'SuperSim', 'Raw', 'Preprocessed', 'Postprocessed' (default)
        site        - e.g. 'SLAC' (default)
        fileFormat  - 'root' (default), 'mat', 'txt' 
        analysis    - e.g. 'All' (default), 'HT', 'LT', 'G133'
        analysisVersion - e.g. '53' (default)
        detector    - e.g. 'All' (default), 'T1Z1'
        DMCVersion  - e.g. '5-3' (default)
        COMSOLVersion - e.g. 5.0 (default)
        """
        CDMSDataset.__init__(self,name,filePath,experiment+'/DMC',site,fileFormat)

        processSteps=['Constants','SuperSim','Raw','Preprocessed','Postprocessed']
        if(processStep in processSteps):
            self.processStep=processStep
        else:
            raise ValueError("Please specify DMC process level (processStep), options are "+str(processSteps))

        #add implementation to path
        self.implement=implement
        self.relativePath+='/'+self.implement

        #add analysis and source to path
        self.relativePath+='/'+analysis+'/'+DMCType

        #add category to path
        if(self.processStep in ['Constants','SuperSim']):
            self.relativePath+='/Input/'+self.processStep
        elif(self.processStep in ['Raw','Preprocessed','Postprocessed']):
            self.relativePath+='/Production/'+self.processStep
        
        #add detector if necessary
        if(self.processStep in ['Constants','Raw','Preprocessed']):
            self.relativePath+='/'+detector

        self.metadata["Analysis"]=analysis
        self.metadata["AnalysisVersion"]=analysisVersion
        self.metadata["COMSOLVersion"]=COMSOLVersion
        self.metadata["Detector"]=detector
        self.metadata["DMCImpl"]=implement
        self.metadata["DMCversion"]=DMCVersion
        self.metadata["Source"]=DMCType
        self.metadata["SourceLoc"]='None'
        self.metadata["EnergyMax"]='-1'
        self.metadata["EnergyMin"]='-1'
        self.metadata["NoiseProfile"]='NA'
        self.metadata["WIMPmass"]="-1"

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
        
        All of these are mandatory; the optional metadata can be specified after construction
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
        CDMSDataset.__init__(self,name,filePath,experiment+'/SuperSim',site,fileFormat)

        #add simulation type to path
        self.relativePath+='/'+SuperSimType+'/'+SuperSimVersion

        self.metadata["SuperSimType"]=SuperSimType
        self.metadata["SuperSimVersion"]=SuperSimVersion

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
                 commentStart = 'None',
                 commentEnd = 'None'):
        '''
        Constructor for the CDMS RawData dataset class
        '''
        

        # instantiate CDMSDataset base object
        CDMSDataset.__init__(self,fileName,filePath,facility,dataLocation,fileFormat)
        self.relativePath += '/R'+str(nFridgeRun)+'/Raw/'+str(series)

        self.metadata["Facility"]=facility
        self.metadata["nFridgeRun"]=int(nFridgeRun)
        self.metadata["nDataType"]=int(nDataType)
        self.metadata["Series"]=series
        self.metadata["nDump"]=int(nDump)
        self.metadata["nEvAll"]=int(nEventsAll)
        self.metadata["nEvBORR"] = int(nEventsBORR)
        self.metadata["nEvEORR"] = int(nEventsEORR)
        self.metadata["nEvBORTS"] =int(nEventsBORTS)
        self.metadata["nEvEORTS"] = int(nEventsEORTS)
        self.metadata["CommentStart"] = commentStart
        self.metadata["CommentEnd"] = commentEnd
        self.metadata["nIsJunk"]=int(nIsJunk)



class ProcessedData(CDMSDataset):

    def __init__(self,
                 fileName, 
                 filePath,
                 facility,
                 nFridgeRun,
                 nDataType,
                 series,
                 prodStep,
                 prodVersion='Test',
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
                 nIsSubMerged=0,
                 nIsMerged=0,
                 analysis = 'All',
                 cutName ='cGood',
                 cutVersion ='0'):
        
        """
        Constructor for the CDMS processed dataset class
        """
        # Some checks
        prodSteps=['Noise','RQ','RRQ','Cut']
        if(not prodStep in prodSteps):
            raise ValueError("Please specify data process level (prodStep), options are "+str(prodSteps))
 
        if nIsSubMerged==1 and nIsMerged==1:
            raise ValueError('Data can not be submerged and merged in the same time. Please check your code')


        # instantiate CDMSDataset base object
        CDMSDataset.__init__(self,fileName,filePath,facility,dataLocation,fileFormat)
   
      
        # Build Data catalog path
        if prodVersion[0:4]=='Prod':
            self.relativePath += '/R'+str(nFridgeRun)+'/Processed/Releases/'+prodVersion
        else:
            self.relativePath += '/R'+str(nFridgeRun)+'/Processed/Tests/'+prodVersion

      
        #add category to path
        if (prodStep == 'Noise'):
            self.relativePath+='/Noise'
        elif (prodStep == 'Cut'):
            self.relativePath+='/Cuts'
        else:
            if nIsSubMerged==1:
                self.relativePath+='/Submerged'
            elif  nIsSubMerged==1:
                self.relativePath+='/Merged'
            else:
                self.relativePath+='/Unmerged/' + series
                

        # metadata
        self.metadata["Facility"]=facility
        self.metadata["nFridgeRun"]=int(nFridgeRun)
        self.metadata["nDataType"]=int(nDataType)
        self.metadata["Series"]=series
        self.metadata["CommentStart"] = commentStart
        self.metadata["CommentEnd"] = commentEnd
        self.metadata["nIsJunk"]=int(nIsJunk)
        self.metadata["ProdStep"] = prodStep
        self.metadata["ProdVersion"] = prodVersion

        if prodStep=='Noise':
            self.metadata["DumpsNoise"] = str(noiseDumps)
                  
        if prodStep=='RQ' or prodStep=='RRQ':
            self.metadata["nEvAll"]=int(nEventsAll)
            self.metadata["nEvBORR"] = int(nEventsBORR)
            self.metadata["nEvEORR"] = int(nEventsEORR)
            self.metadata["nEvBORTS"] =int(nEventsBORTS)
            self.metadata["nEvEORTS"] = int(nEventsEORTS)
               
            if nIsSubMerged==0 and nIsMerged==0:
                self.metadata["nDump"]=int(nDump)
            else:
                self.metadata["Dumps"] = str(nDump)

        self.metadata["Processing_config"] = processing_config
        self.metadata["Analysis_config"] = analysis_config
        if prodStep=='RRQ':
            self.metadata["Calib_processing_config"] = calib_processing_config
            self.metadata["Calibration_config"] = calibration_config
        


        if prodStep=='Cut':
            self.metadata["Analysis"] = analysis
            self.metadata["CutName"] = cutName
            self.metadata["CutVersion"] = cutVersion
