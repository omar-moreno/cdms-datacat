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

    def ls(self,path):
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

    def search(self,dtype='',subDtype='',group='',site=None,query=None):
        path="/CDMS/"
        if(dtype != ''):
            path=path+dtype+"/"
            if(subDtype != ''):
                path=path+subDtype+"/"
                if(group != ''):
                    path=path+group+"/"
        print path
        return self.client.search(path+'**',site=site,query=query)

    def add(self,CDMSds):
        try:
            self.client.mkds(CDMSds.relativePath,
                             CDMSds.datasetName,
                             CDMSds.fileType,
                             CDMSds.fileFormat,
                             versionMetadata=CDMSds.metadata,
                             resource=CDMSds.filePath,
                             site=CDMSds.site)
        except:
            print "Could not create dataset"

def class CDMSDataset:
    
    def __init__(self,name,filePath,dataGroup,dataType,site,fileFormat=None,fileType=None,DMCType=None):
        self.metadata = Metadata()
        self.datasetName=name
        self.dataType=dataType
        self.site=site
        self.fileFormat=fileFormat
        self.fileType=fileType
        self.filePath=filePath

        if(dataType='TF'):
            self.metadata["fridgeName"]="doughtyFridge"
            self.metadata["Temp"]=0.07

            self.relativePath='/CDMS/TF/'+site+'/'+dataGroup
        elif(dataType='DMC'):

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
            self.metadata["simulationSubType"]='vac'
            self.metadata["WIMPmass"]="-1"
        elif(dataType='Soudan'):
            self.metadata["run"]='NA'
        elif(dataType='SNOLAB'):
            self.metadata["run"]='NA'
            
        self.metadata["processProg"]="NA"
        self.metadata["processProgVersion"]="-1"
        self.metadata["processParadigm"]="-1"
