#!/usr/bin/env python

#includes
import os
import numpy
import glob
from CDMSDataCatalog import *

#create Data catalog object
dc=CDMSDataCatalog()

#file paths for DMC/Processed Data
baseDir='/nfs/slac/g/cdms/u05/'
outputDir=baseDir+'DetMC_data/CDMS_DMC_v4-1-4_20120604_v02/R133_LT_DMC_COMSOL5_Epot/'
procDir=baseDir+'DMC_dataRelease/CDMS_DMC_v4-1-4_20120604_v02/LT-R133_DMC-4-Prodv5-3-6/'

#dataset specifics (these could be looped over)
dataset='Cf_cryo'   #dataset name
simSource='Cf'      #calibration source
subdir='cf'         #processed data subdirectory (after merged/all)
simSourceLoc='cryo' #info about source location or varied DMC input
bulldozed='1'       #0 for false, 1 for true
analysis='LT'       #analysis DMC run made for

#this function is used to create and add dataset objects independent of the file exploration below
def makeDS(filePath,processStep,detector):

    #determine file format
    if 'EPot' in filePath:
        fileFormat='epot'
    elif '.mat' in filePath:
        fileFormat='mat'
    elif '.m' in filePath:
        fileFormat='m'
    elif '.root' in filePath:
        fileFormat='root'
    else:
        fileFormat='txt'

    # use file name as dataset name
    dsName=os.path.split(filePath)[1]
    # create DMC data structure (from CDMSDataCatalog package)
    ds = DMCData(dsName,
                 filePath,
                 dataset,
                 processStep=processStep,
                 site='SLAC',
                 fileFormat=fileFormat,
                 analysis=analysis,
                 analysisVersion='53',
                 detector=detector)
    # add custom metadata
    ds['Bulldozed']=bulldozed
    ds['Source']=simSource
    ds['DataLevel']=processStep
    ds['SourceLoc']=simSourceLoc
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

#######################
## commit DMC output ##
#######################

# get DMC directory
DMCDir=outputDir+dataset+'/'
# find subdirectories
DMCDirs=glob.glob(DMCDir+'*DMC*')
dets=numpy.arange(1101,1116)
#loop over SCDMS detectors
for det in dets:
    #get TXZY string
    detStr = GetDetStr(det)
    #loop over subdirectories
    for d in DMCDirs:
        #if current detector is in the subdirectory string
        if(detStr in d):
            #get constants directory
            tmpDir=d+'/Constants/'
            #find constants files
            files=glob.glob(tmpDir+'*.m*')
            #for each file, make dataset, and add
            for f in files:
                makeDS(f,'Constants',detStr)

            #get input directory
            tmpDir=d+'/Input/'
            #find input files (should only be one)
            files=glob.glob(tmpDir+'*.mat')
            #loop over files, make dataset, add
            for f in files:
                makeDS(f,'SuperSim',detStr)

            #add one each of ResultsPhonon, ResultsTES, ResultsFET
            for directory in ['Phonon','TES','FET']:
                tmpDir=d+'/Results'+directory+'/'
                #find input files
                files=sorted(glob.glob(tmpDir+'*1.mat'))
                if(len(files) > 0):
                    makeDS(files[0],'Raw',detStr)

            #add one each of text_files_DMCtemplate
            for directory in ['_DMCtemplate']:
                tmpDir=d+'/text_files'+directory+'/'
                #find input files
                files=sorted(glob.glob(tmpDir+'*1.txt'))
                if(len(files) > 0):
                    makeDS(files[0],'Preprocessed',detStr)

            #add lines here to commit any other data from the DMC folder


#commit processed DMC data
BatsDir=procDir+dataset+'/merged/'
files=glob.glob(BatsDir+'*.root')
if(len(files) < 1):
    BatsDir=procDir+dataset+'/merged/all/'+subdir+'/'
    files=glob.glob(BatsDir+'*.root')
for f in files:
    makeDS(f,'Postprocessed','All')
