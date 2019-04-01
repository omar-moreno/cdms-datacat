import datacat
from datacat import client_from_config_file
from datacat.model import Metadata
import pathlib


def corrPathCDMS(path):
    if(path[0] != '/'):
        path="/"+path
        
    if(path[1:5] != "CDMS"):
        path="/CDMS"+path
        
    return path

def getFileFormat(filePath):
    return ''.join(pathlib.Path(filePath).suffixes).strip('.')

class CDMSDataCatalog:
    
    def __init__(self,config_file=None):
        self.client = client_from_config_file(config_file) if config_file else client_from_config_file()

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

    def search(self,path,site=None,query=None, sort=None, show=None):
        path=corrPathCDMS(path)
        results=self.client.search(path,site=site,query=query, sort=sort,show=show)
        convResults=list()
        for result in results:
            convResults.append(CDMSDataset.fromSearchDataset(result))
        return convResults

    def get(self,path,site='All'):
        path=corrPathCDMS(path)
        return CDMSDataset.fromDataset(self.client.path(path,site=site))

    def add(self,CDMSds,replace=True):
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
            print(e)
            print("Could not create dataset")
                 
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
        nds = cls(str(ds.name),str(ds.resource),
                  dataType='DatacatQuery',
                  site=str(ds.site),
                  fileFormat=str(ds.fileFormat))
        nds.relativePath=str(ds.path)
        for k,v in ds.versionMetadata.items():
            nds.metadata[k]=v
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
        return nds

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
                 processStep,
                 prodVersion='Test',
                 dataLocation='SLAC',
                 fileFormat='root',
                 commentStart = 'None',
                 commentEnd = 'None',
                 nIsJunk=0,
                 nDump = 0,
                 noiseDumps = '0',
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
        processSteps=['Noise','RQ','RRQ','Cut']
        if(not processStep in processSteps):
            raise ValueError("Please specify data process level (processStep), options are "+str(processSteps))
 
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
        if (processStep == 'Noise'):
            self.relativePath+='/Noise'
        elif (processStep == 'Cut'):
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
        self.metadata["ProdStep"] = processStep
        self.metadata["ProdVersion"] = prodVersion

        if processStep=='Noise':
            self.metadata["DumpsNoise"] = str(noiseDumps)
                  
        if processStep=='RQ' or processStep=='RRQ':
            self.metadata["nEvAll"]=int(nEventsAll)
            self.metadata["nEvBORR"] = int(nEventsBORR)
            self.metadata["nEvEORR"] = int(nEventsEORR)
            self.metadata["nEvBORTS"] =int(nEventsBORTS)
            self.metadata["nEvEORTS"] = int(nEventsEORTS)
               
            if nIsSubMerged==0 and nIsMerged==0:
                self.metadata["nDump"]=int(nDump)

        if processStep=='Cut':
            self.metadata["Analysis"] = analysis
            self.metadata["CutName"] = cutName
            self.metadata["CutVersion"] = CutVersion
