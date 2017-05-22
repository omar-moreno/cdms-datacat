#!/usr/bin/env python

#includes
import os
import numpy
import glob
from CDMSDataCatalog import *
from DMCCatTools import *
import sys

if len(sys.argv) < 5:
    print sys.argv
    print "Usage:  python addDMCdata.py analysis dataset simSource mergedir mergedsubdir [simSourceLoc]"
    exit(1)
else:
    argv=sys.argv
    analysis=argv[1]
    dataset=argv[2]
    simSource=argv[3]
    mergedir=argv[4]
    subdir=argv[5]

if len(sys.argv) > 6:
    simSourceLoc=sys.argv[6]
else:
    for thloc in ['cryo','vacuum','sidewall','surface']:
        if thloc in dataset : 
            simSourceLoc=thloc
            break;
        else : simSourceLoc='NA'


print "Setting up:"
print analysis,dataset,simSource,mergedir,subdir,simSourceLoc
print "______"

#create Data catalog object
dc=CDMSDataCatalog()

#file paths for DMC/Processed Data
baseDir='/nfs/slac/g/cdms/u05/DMCProduction/V1-4/'
outputDir=baseDir+'Raw/'+analysis+'/'
procDir=baseDir+'Processed/'+analysis+'/'
BatsDir=procDir+'/'+mergedir+'/merged/'


bulldozed='Not Used'       #0 for false, 1 for true
ProdVer='MATLAB_V1-4'
tesode='TES_ODE_v1.2'
PreProcVer='DMCPreBats_v2.1'
ProcVer='cdmsbats_5.5.2'

print "This has been selected for pushing into the catalog:"
print dataset,simSource,subdir,simSourceLoc,bulldozed,analysis


#######################
## commit DMC output ##
#######################

# get DMC directory
DMCDir=outputDir+dataset+'/'
# find subdirectories
DMCDirs=glob.glob(DMCDir+'*Soudan*')

print "Looking for Sample in Directory:",DMCDir

dets=numpy.arange(1101,1116)
#loop over SCDMS detectors
for det in dets:
    print det
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
                makeDS(f,dataset,'Constants',detStr,analysis,simSource,simSourceLoc,bulldozed=bulldozed,DMCVersion=ProdVer,TESODE=tesode,PreProcVer=PreProcVer,ProcVer=ProcVer)

            #get input directory
            tmpDir=d+'/Input/'
            #find input files (should only be one)
            files=glob.glob(tmpDir+'*.mat')
            #loop over files, make dataset, add
            for f in files:
                makeDS(f,dataset,'SuperSim',detStr,analysis,simSource,simSourceLoc,bulldozed=bulldozed,DMCVersion=ProdVer,TESODE=tesode,PreProcVer=PreProcVer,ProcVer=ProcVer)

            #add one each of ResultsPhonon, ResultsTES, ResultsFET
            for directory in ['Phonon','PhononBull','TES','FET']:
                tmpDir=d+'/Results'+directory+'/'
                #find input files
                files=sorted(glob.glob(tmpDir+'*1.mat'))
                if(len(files) > 0):
                    makeDS(files[0],dataset,'Raw',detStr+'/Results'+directory,analysis,simSource,simSourceLoc,bulldozed=bulldozed,DMCVersion=ProdVer,TESODE=tesode,PreProcVer=PreProcVer,ProcVer=ProcVer)

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
                makeDS(f,dataset,'Preprocessed',detStr+'/calib_files',analysis,simSource,simSourceLoc,bulldozed=bulldozed,DMCVersion=ProdVer,TESODE=tesode,PreProcVer=PreProcVer,ProcVer=ProcVer)

            outFiles=glob.glob(tmpDir+'out*.mat')
            for f in outFiles:
                makeDS(f,dataset,'Preprocessed',detStr+'/calib_files',analysis,simSource,simSourceLoc,bulldozed=bulldozed,DMCVersion=ProdVer,TESODE=tesode,PreProcVer=PreProcVer,ProcVer=ProcVer)

            #add validTool
            tmpDir=d+'/validTool/'
            files=glob.glob(tmpDir+'*')
            for f in files:
                if('plots' in f):
                    plots=glob.glob(f+'/*.png')
                    for plot in plots:
                        makeDS(plot,dataset,'Preprocessed',detStr+'/validTool/plots',analysis,simSource,simSourceLoc,bulldozed=bulldozed,DMCVersion=ProdVer,TESODE=tesode,PreProcVer=PreProcVer,ProcVer=ProcVer)
                else:
                    makeDS(f,dataset,'Preprocessed',detStr+'/validTool',analysis,simSource,simSourceLoc,bulldozed=bulldozed,DMCVersion=ProdVer,TESODE=tesode,PreProcVer=PreProcVer,ProcVer=ProcVer)


#find combined files
# find subdirectories                                                                                                                                                           
print " finding ROOT files"                     
ROOTDirs=glob.glob(DMCDir+'ROOT*')
for d in ROOTDirs:
    dirName='combined_ROOT_files_T2Z1only'
    files=glob.glob(d+'/*.root')
    if (len(files) == 0):
        files=glob.glob(d+'/*/combined_ROOT_files_T2Z1only/*.root')
    if (len(files) > 0):    
        makeDS(files[0],dataset,'Preprocessed',dirName,analysis,simSource,simSourceLoc,bulldozed=bulldozed,DMCVersion=ProdVer,TESODE=tesode,PreProcVer=PreProcVer,ProcVer=ProcVer)
    else:
        dirs=glob.glob(d+'/*')
        for dd in dirs:
            files=glob.glob(dd+'/*_0.root')
            dirName=os.path.basename(dd)
            if(len(files) > 0):
                makeDS(files[0],dataset,'Preprocessed',dirName,analysis,simSource,simSourceLoc,bulldozed=bulldozed,DMCVersion=ProdVer,TESODE=tesode,PreProcVer=PreProcVer,ProcVer=ProcVer)

#commit processed DMC data
print "Looking for postprocessed files:"
print BatsDir

files=glob.glob(BatsDir+'*.root')
if(len(files) < 1):
    BatsDir=procDir+'/'+mergedir+'/merged/all/'+subdir+'/'
    print BatsDir
    files=glob.glob(BatsDir+'*.root')
for f in files:
    makeDS(f,dataset,'Postprocessed',mergedir,analysis,simSource,simSourceLoc,bulldozed=bulldozed,DMCVersion=ProdVer,TESODE=tesode,PreProcVer=PreProcVer,ProcVer=ProcVer)

