#This checks all the file sizes of everything being copied over, just to be kind :)

#RAW DATA
#Original
orig1 = '/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR68dm/'
orig2 = '/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR70/'
orig3 = '/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR70/PMTDAQ'  #This one is weird, save it for later

#New
new1 = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R68/Raw/'
new2 = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R70/Raw/' #Kinda ignore the root files for now...

#PROCESSED DATA
#original

#new
#we still have yet to figure this out... But that's not worrying me

import os

def getFileSize(filePath):
    '''
    Returns the filesize
    '''
    return os.path.getsize(filePath)

print("AR68dm", getFileSize(orig1))
print("AR70", getFileSize(orig2))
print("PMTDAQ", getFileSize(orig3))


