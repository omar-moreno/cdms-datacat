import datacat
from datacat import client_from_config_file
from datacat.model import Metadata

def corrPathCDMS(path):
    if(path[0] != '/'):
        path="/"+path
        
    if(path[1:5] != "CDMS"):
        path="/CDMS"+path
        
    return path

class CDMSDataCatalog:
    
    def __init__(self):
        self.client = client_from_config_file()

    def ls(self,path='/'):
        path=corrPathCDMS(path)
        try:
            for child in self.client.children(path):
                print child.path
        except TypeError:
            print "Cannot ls, "+path+" is a dataset"
        except:
            print "Path does not exist"

    def rm(self,path,recursive=False,verbose=True):
        path=corrPathCDMS(path)
        
        if(verbose):
            print path
        if(recursive):
            try:
                if(type(self.client.path(path)) == datacat.model.Dataset):
                    self.client.rmds(path)
                    return
            except Exception as e:
                print "Couldn't delete "+path
                return

            else:
                for child in self.client.children(path):
                    self.rm(child.path,recursive=True)

                ctype='folder'
                if(type(self.client.path(path)) == datacat.model.Group):
                    ctype='group'
                
                if(verbose):
                    print path
                try:
                    self.client.rmdir(path,type=ctype)
                except Exception as e:
                    print "Couldn't delete "+path
                return
        else:
            try:
                if(type(self.client.path(path)) == datacat.model.Dataset):
                    self.client.rmds(path)
                else:
                    self.client.rmdir(path)
            except Exception as e:
                print e
                raise IOError("Couldn't delete "+path)

    def mkdir(self,path,parents=False):
        path=corrPathCDMS(path)
        self.client.mkdir(path,parents=parents)
        return

    def search(self,path,group='**',site=None,query=None,show=None):
        path=corrPathCDMS(path)
        path=path+group
        print path
        return self.client.search(path,site=site,query=query,show=show)

    def add(self,CDMSds,replace=True):
        try:
            path=corrPathCDMS(CDMSds.relativePath)
            if(not self.client.exists(path)):
                self.mkdir(path,parents=True)
            DSexists = self.client.exists(path+'/'+CDMSds.datasetName)
            if(DSexists):
                if(replace):
                    print 'Replacing existing dataset: '+path+'/'+CDMSds.datasetName
                    self.rm(path+'/'+CDMSds.datasetName)
                else:
                    print 'Skipping existing dataset: '+path+'/'+CDMSds.datasetName

            if(not DSexists or replace):
                self.client.mkds(path,
                                 CDMSds.datasetName,
                                 CDMSds.fileType,
                                 CDMSds.fileFormat,
                                 versionMetadata=CDMSds.metadata,
                                 resource=CDMSds.filePath,
                                 site=CDMSds.site)
        except Exception as e:
            print e
            print "Could not create dataset"
                 
class CDMSDataset:
    """Base class for CDMS datasets"""
    
    fileTypes={'m':'M','mat':'CDMSMATLAB','root':'CDMSROOT','txt':'CDMSTXT','epot':'CDMSEPOT','supersim':'CDMSHISTOGRAMS'}
    fileFormats={'m':'m','mat':'mat','root':'root','txt':'txt','epot':'mat','supersim':'root'}

    def __init__(self,
                 name, 
                 filePath,
                 dataType='Test',
                 site='SLAC',
                 fileFormat='txt'):
        """Constructor for the CDMS dataset base class
        
        All of these are mandatory; the optional metadata can be specified after construction
        name - dataset name
        filePath - physical path to file
        dataType - 'DMC', 'Soudan', 'SNOLAB', 'TF', etc
        site -  e.g. 'SLAC'
        fileFormat - e.g. 'root', 'mat', 'txt', 'm', 'epot'
        
        """
        self.datasetName=name
        self.filePath=filePath
        self.setDataType(dataType)
        self.setSite(site)
        self.setFileFormat(fileFormat)
        self.relativePath='/CDMS/'+self.dataType
        
        self.metadata = Metadata()

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
        print "Name:         "+self.datasetName
        print "System Path:  "+self.filePath
        print "Catalog Path: "+self.relativePath 
        print "Site:         "+self.site
        print "Data Type:    "+self.dataType
        print "File Format:  "+self.fileFormat
        print "File Type:    "+self.fileType
        print "Metadata:"
        for k,v in self.metadata.iteritems():
            print "  - "+k+": "+str(v)

    def __str__(self):
        return '<Name: '+self.datasetName+ ', Path: '+self.relativePath+', File: '+self.filePath+'>'

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
        if(self.processStep in ['Constants','Raw']):
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
