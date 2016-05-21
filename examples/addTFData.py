#!/usr/bin/env python

#includes
import sys
import os
import numpy
import glob
from CDMSDataCatalog import *

#create Data catalog object
dc=CDMSDataCatalog()

#this function is used to create and add dataset objects independent of the file exploration below
def makeDS(filePath):

    #get UMN ID from database
    id=-1 #put query function here
    umn_location_tag='tagvalue' #put query function here

    #determine file type
    fileFormat=getFileFormat(filePath)
    # use file name as dataset name
    dsName=os.path.split(filePath)[1]
    # create SuperSim data structure (from CDMSDataCatalog package)
    ds = TestFridgeData(dsName,
                        filePath,
                        'UMN/TFname',
                        site='SLAC',
                        fileFormat=fileFormat)
    # add custom metadata
    ds['run']=id
    ds['location_tag']=umn_location_tag

    # output dataset info
    ds.info()
    # add to catalog
    dc.add(ds,replace=False)

for i in range(1,len(sys.argv)):
    filename=sys.argv[i]
    print filename
    makeDS(filename)
