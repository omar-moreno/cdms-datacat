#!/usr/bin/env python 
#includes            
import os
import numpy
import glob
from CDMSDataCatalog import *
from DMCCatTools import*
import sys

#this function is used to create and add dataset objects independent of the file exploration below

dc=CDMSDataCatalog()

def makeDS(filePath,dataset,processStep,detector,analysis,simSource,simSourceLoc,bulldozed='0',DMCVersion='MATLAB_V1-3',TESODE=True,PreProcVer='PreBats_v2.0',ProcVer='cdmsbats_v5.4.3'):
    
    #determine file format
    if 'EPot' in filePath:
        fileFormat='epot'
    elif '.mat' in filePath:
        fileFormat='mat'
    elif '.m' in filePath:
        fileFormat='m'
    elif '.root' in filePath:
        fileFormat='root'
    elif '.png' in filePath:
        fileFormat='png'
    else:
        fileFormat='txt'

    # use file name as dataset name
    dsName=os.path.split(filePath)[1]
    # create DMC data structure (from CDMSDataCatalog package)
    ds = DMCData(dsName,
                 filePath,
                 dataset,
                 processStep=processStep,
                 experiment='Soudan',
                 implement=DMCVersion,
                 site='SLAC',
                 fileFormat=fileFormat,
                 analysis=analysis,
                 analysisVersion='54',
                 detector=detector,
                 DMCVersion='4-2',
                 COMSOLVersion='5.2'
    )
    # add custom metadata
    ds['Bulldozed']=bulldozed
    ds['TES_ODE']=str(TESODE)
    ds['Source']=simSource
    ds['DataLevel']=processStep
    ds['SourceLoc']=simSourceLoc
    ds['Preprocessing']=PreProcVer
    ds['Processing']=ProcVer
    
    if(processStep == 'Postprocessed'):
        if('calib' in dsName):
            ds['DataLevel']='RRQ'
        elif('merge' in dsName):
            ds['DataLevel']='RQ'
    # output dataset info
    print ds.relativePath, ds.datasetName, ds.fileType, ds['DataLevel']
    # add to catalog
    dc.add(ds,replace=False)

########################
#End user modifications#
########################

def GetDetStr(detnum):
    dn=int(detnum-1100)
    t= (dn+2)/3
    z= (dn-1)%3+1
    detector="T"+str(t)+"Z"+str(z)
    return detector


