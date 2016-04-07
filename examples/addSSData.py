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
ssDir=baseDir+'path/to/files/'

SuperSimVersion=1.0
SuperSimType='Backgrounds'

#this function is used to create and add dataset objects independent of the file exploration below
def makeDS(filePath,SuperSimVersion=1.0,SuperSimType='Backgrounds'):

    #determine file type
    fileFormat=getFileFormat(filePath)
    # use file name as dataset name
    dsName=os.path.split(filePath)[1]
    # create SuperSim data structure (from CDMSDataCatalog package)
    ds = SuperSimData(dsName,
                      filePath,
                      SuperSimType,
                      SuperSimVersion,
                      site='SLAC',
                      fileFormat=fileFormat)
    # add custom metadata
    ds['newItem']='value'
    # output dataset info
    ds.info()
    # add to catalog
    dc.add(ds,replace=False)

#commit SS files 
files=glob.glob(SSdataDir+'*.root')
for f in files:
    makeDS(f,SuperSimVersion=SuperSimVersion,SuperSimType=SuperSimType)
