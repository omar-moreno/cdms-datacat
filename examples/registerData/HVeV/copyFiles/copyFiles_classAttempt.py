#The purpose of this program is to copy files from the original locations to the new locations
    #Original Locations:
        #/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR68dm/[not quite series]/*.hdf5
        #/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR70/[not quite series]/*.hdf5
        #/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR70/PMTDAQ/day*/Raw/[not quite series]/*.root

    #New Location:
        #/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R68/Raw/[Series]/*.hdf5
        #/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R70/Raw/[Series]/*.hdf5
        #/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R70/Raw/[Series]/*.root

#Import the modules you need
import os, shutil

#Specify all the original and new paths

#Original
orig1 = '/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR68dm/'
orig2 = '/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR70/'
orig3 = '/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR70/PMTDAQ'  #This one is weird, save it for later

#New
new1 = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R68/Raw/'
new2 = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R70/Raw/' #Ignore the ROOT files!

#Create a class to contain the copy files
class copyFiles:
    def __init__(self, orig, new):
        '''
        Constructor for the copyFiles class

        Description of copyFiles:
            This will copy files over, and make sure there are no pre-existing files already
            Copying will happen via shutil

        Arguments:
            orig - original path/directory that needs copying
            new - new path/directory to copy to
        '''
        
        self.origpath = orig
        self.newpath = new
        self.walkdir(self.origpath)

    def forDir(self, origdir):
        '''
        Function for copyFiles class that returns the 
        '''
        for path in origdir:
            

    def walkdir(self, path):
        self.odir = os.listdir(path = path)
        return self.odir
        

def main():
    copy = copyFiles(orig1, new1)
    jimmy = copyFiles(orig1, new1)
    jimmy.forDir()

if __name__ == "__main__":
    main()
     



