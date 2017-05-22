#!/usr/bin/env python

#includes
import os
import numpy
import glob
from CDMSDataCatalog import *
import sys

if len(sys.argv) < 4:
    print sys.argv
    exit(1)
else:
    argv=sys.argv
    dataset=argv[1]
    simSource=argv[2]
    subdir=argv[3]

if len(sys.argv) > 4:
    simSourceLoc=sys.argv[4]
else:
    simSourceLoc='NA'

print "Setting up:"
print dataset,simSource,subdir,simSourceLoc
print "______"

#create Data catalog object
dc=CDMSDataCatalog()

#file paths for DMC/Processed Data
baseDir='/nfs/slac/g/cdms/u02/'
outputDir=baseDir+'DetMC_Data/CDMS_DMC_v4-2-0_20160701_v1-1/HT_DMC_COMSOL5_Epot/'
procDir=baseDir+'DMC_dataRelease/CDMS_DMC_v4-2-0_20160701_v1-1/HT_DMC_COMSOL5_Epot/'

#if('bull' in dataset):
bulldozed='1'       #0 for false, 1 for true
#else:
#    bulldozed='0'

analysis='HT'       #analysis DMC run made for

print "This has been selected for pushing into the catalog:"
print dataset,simSource,subdir,simSourceLoc,bulldozed,analysis

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
                 implement='MATLAB_V1-1',
                 site='SLAC',
                 fileFormat=fileFormat,
                 analysis=analysis,
                 analysisVersion='53',
                 detector=detector,
                 DMCVersion='4-2',
                 COMSOLVersion='5.2'
    )
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

print "Looking for Sample in Directory:",DMCDir

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
                    makeDS(files[0],'Raw',detStr+'/Results'+directory)

            #add one each of text_files_*
            #for directory in ['','_DMCtemplate','_gamma_fit_cal','_qmean']:
            #    tmpDir=d+'/text_files'+directory+'/'
            #    #find input files
            #    files=sorted(glob.glob(tmpDir+'*_1.txt'))
            #    for f in files:
            #        makeDS(f,'Preprocessed',detStr+'/text_files'+directory)

            #add one example of calib_files
            tmpDir=d+'/calib_files/'
            files=glob.glob(tmpDir+'*fit_calibration*.mat')
            for f in files:
                makeDS(f,'Preprocessed',detStr+'/calib_files')
            outFiles=glob.glob(tmpDir+'out*.mat')
            for f in outFiles:
                makeDS(f,'Preprocessed',detStr+'/calib_files')

            #add validTool
            tmpDir=d+'/validTool/'
            files=glob.glob(tmpDir+'*')
            for f in files:
                if('plots' in f):
                    plots=glob.glob(f+'/*.png')
                    for plot in plots:
                        makeDS(plot,'Preprocessed',detStr+'/validTool/plots')
                else:
                    makeDS(f,'Preprocessed',detStr+'/validTool')

#find combined files
# find subdirectories                                                                                                                                                                                
ROOTDirs=glob.glob(DMCDir+'ROOT*')
for d in ROOTDirs:
    dirName='combined_ROOT_files_T2Z1only'
    files=glob.glob(d+'/*.root')
    if (len(files) == 0):
        files=glob.glob(d+'/*/combined_ROOT_files_T2Z1only/*.root')
    if (len(files) > 0):    
        makeDS(files[0],'Preprocessed','combined_ROOT_files_T2Z1only')
    else:
        dirs=glob.glob(d+'/*')
        for dd in dirs:
            files=glob.glob(dd+'/*_0.root')
            dirName=os.path.basename(dd)
            if(len(files) > 0):
                makeDS(files[0],'Preprocessed',dirName)

#commit processed DMC data
BatsDir=procDir+dataset+'/merged/'
files=glob.glob(BatsDir+'*.root')
if(len(files) < 1):
    BatsDir=procDir+dataset+'/merged/all/'+subdir+'/'
    files=glob.glob(BatsDir+'*.root')
for f in files:
    makeDS(f,'Postprocessed','All')


