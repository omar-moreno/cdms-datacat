import datacat
from datacat import client_from_config_file

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
