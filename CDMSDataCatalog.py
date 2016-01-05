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

    def mkdir(self,path):
        path=corrPathCDMS(path)
        self.client.mkdir(path)
        return

    def search(self,path,group='**',site=None,query=None,show=None):
        path=corrPathCDMS(path)
        path=path+group
        print path
        return self.client.search(path,site=site,query=query,show=show)

    def add(self,CDMSds):
        try:
            path=corrPathCDMS(CDMSds.relativePath)
            print "Committing "+CDMSds.datasetName
            print path
            print CDMSds.fileType
            print CDMSds.fileFormat
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
    
    def __init__(self,
                 name, 
                 filePath,
                 dataGroup,
                 dataType,
                 site,
                 fileFormat,
                 fileType,
                 DMCType=None,
                 release=None,
                 run=None,
                 runData=None,
                 runType=None):
        """Constructor for the CDMS specific datset class
        
        All of these are mandatory; the optional metadata can be specified after construction
        name - dataset name
        filePath - physical path to file
        dataGroup - e.g. 'RQdata' or 'RRQdata' (last organization level)
        dataType - ('TF', 'DMC', 'Soudan', 'SNOLAB')
        site -  e.g. 'SLAC'
        fileFormat - e.g. 'root', 'mat', 'txt' 
        fileType - e.g. 'CDMSROOT', 'CDMSMAT', 'CDMSRAW'

        Mandatory for Soudan Data:
        release - 'Prodv5-3_June2013'
        run - 'R133','R134'
        runData - 'all','merged','cuts',...
        runType - 'cf','ba','bg_permitted_Sept2013'

        Mandatory for DMC Data:
        DMCType - 'Cf','Ba','WIMP',...
        """
        self.datasetName=name
        self.filePath=filePath

        self.dataType=dataType
        self.site=site
        self.fileFormat=fileFormat
        self.fileType=fileType
        
        self.metadata = Metadata()

        dataTypes=['TF','DMC','Soudan','SNOLAB']
        if not (dataType in dataTypes):
            raise ValueError("Please choose one of the following Data Types:"+str(dataTypes))

        if(dataType=='TF'):
            self.metadata["fridgeName"]="doughtyFridge"
            self.metadata["Temp"]=0.07

            sites=['UCB','UMN','SLAC','TAMU','CUTE']
            if not (site in sites):
                raise ValueError("The following test fridge sites are currently supported: "+str(sites))

            self.relativePath='/CDMS/TF/'+site+'/'+dataGroup
        elif(dataType=='DMC'):

            DMCTypes=['Cf','Ba','WIMP']
            if(DMCType in DMCTypes):
                self.DMCType=DMCType
            else:
                raise ValueError("Please specify DMC Type: "+str(DMCTypes))

            dataGroups=['RQdata','RRQdata']
            if (dataGroup in dataGroups):
                self.group=dataGroup
            else:
                raise ValueError("Please specify DMC data group: "+str(dataGroups))

            self.relativePath='/CDMS/DMC_dataRelease/'+DMCType+'/'+dataGroup

            self.metadata["analysis"]='NA'
            self.metadata["analysisVersion"]='NA'
            self.metadata["COMSOLVersion"]='X.X'
            self.metadata["dataType"]='CDMSROOT'
            self.metadata["detectors"]='TXZY'
            self.metadata["detectorType"]='iZIPX'
            self.metadata["DMCversion"]='5-3'
            self.metadata["energyMax"]='-1'
            self.metadata["energyMin"]='-1'
            self.metadata["noiseProfile"]='NA'
            self.metadata["simulationSubType"]='-1'
            self.metadata["WIMPmass"]="-1"
        elif(dataType=='Soudan'):
            self.metadata["analysis"]='NA'
            self.metadata["analysisVersion"]='NA'

            runs=['R133','R134','R135']
            if not (run in runs):
                raise ValueError("Please specify Soudan run: "+str(runs))
            self.metadata["run"]=run

            releases=['Prodv5-3_June2013','Prodv5-3-5']
            if not (release in releases):
                raise ValueError("Please specify Soudan release: "+str(releases))

            runDatas=['all','byseries','cuts','cuts_HT']
            if not (runData in runDatas):
                raise ValueError("Please specify run data type: "+str(runDatas))

            runTypes=['bg_permitted_Sept2013','ba','cf']
            if not (runType in runTypes):
                raise ValueError("Please specify run type: "+str(runTypes))

            self.relativePath='/CDMS/Soudan/'+run+'/'+release+'/'+runData+'/'+runType+'/'+dataGroup
        elif(dataType=='SNOLAB'):
            self.metadata["run"]='NA'
            self.metadata["analysis"]='NA'
            self.metadata["analysisVersion"]='NA'
            self.relativePath='/CDMS/SNOLAB/'
            
        self.metadata["processProg"]="NA"
        self.metadata["processProgVersion"]="-1"
        self.metadata["processParadigm"]="-1"

    
    def info(self):
        """Neatly output all information in dataset structure"""
        print "Name: "+self.datasetName
        print "System Path: "+self.filePath
        print "Site: "+self.site
        print "Data Type "+self.dataType
        print "File Format: "+self.fileFormat
        print "File Type: "+self.fileType
        print "Metadata:"
        for k,v in self.metadata.iteritems():
            print "  "+k+": "+str(v)
