import datacat
from datacat import client_from_config_file
import pathlib

from .fetch import fetchdata
from .CDMSDataset import CDMSDataset


def corrPathCDMS(path):
    if(path[0] != '/'):
        path = "/"+path

    if(path[1:5] != "CDMS"):
        path = "/CDMS"+path

    return path


def getFileFormat(filePath):
    return ''.join(pathlib.Path(filePath).suffixes).strip('.')


class CDMSDataCatalog:
    def __init__(self, config_file=None):
        self.client = client_from_config_file(
            config_file) if config_file else client_from_config_file()
        # todo: get default location from config file
        self.defaultDataRoot = 'datacat_data'

    def ls(self, path='/CDMS/'):
        """ Return contents of a datacat path, by default look in /CDMS/ """
        path = corrPathCDMS(path)
        try:
            for child in self.client.children(path):
                print(child.path)
        except TypeError:
            print("Cannot ls, %s is a dataset" % path)
        except BaseException:
            print("Path does not exist")

    def exist(self, path, versionId=None, site=None):
        path = corrPathCDMS(path)
        do_exist = self.client.exists(path, versionId, site)
        return do_exist

    def rm(self, path, recursive=False, verbose=True):
        path = corrPathCDMS(path)

        if(verbose):
            print(path)
        if(recursive):
            try:
                if(type(self.client.path(path)) == datacat.model.Dataset):
                    self.client.rmds(path)
                    return
            except Exception:
                print("Couldn't delete %s" % path)
                return

            else:
                for child in self.client.children(path):
                    self.rm(child.path, recursive=True)

                ctype = 'folder'
                if(type(self.client.path(path)) == datacat.model.Group):
                    ctype = 'group'

                if(verbose):
                    print(path)
                try:
                    self.client.rmdir(path, type=ctype)
                except Exception:
                    print("Couldn't delete %s" % path)
                return
        else:
            try:
                if(type(self.client.path(path)) == datacat.model.Dataset):
                    self.client.rmds(path)
                else:
                    self.client.rmdir(path)
            except Exception as e:
                print(e)
                raise IOError("Couldn't delete "+path)

    def mkdir(self, path, parents=False):
        path = corrPathCDMS(path)
        self.client.mkdir(path, parents=parents)
        return

    def search(self, path, *args, **kwargs):
        path = corrPathCDMS(path)
        results = self.client.search(path, *args, **kwargs)
        # results come back unsorted, which is not what we want
        results.sort(key=lambda res: res.path)
        return list(CDMSDataset.fromSearchDataset(res) for res in results)

    def get(self, path, site='All'):
        """Convert a path (string) to a full CDMSDataset object"""
        path = corrPathCDMS(path)
        return CDMSDataset.fromDataset(self.client.path(path, site=site))

    def add(self, CDMSds, replace=True, catch_errors=True):
        """Add a new CDMSDataset entry to the catalog
        Args:
            CDMSds (CDMSDataset): The new dataset to add
            replace (bool):  If true, overwrite an existing entry at that path
            catch_errors (bool): If False, allow errors to propagate
        """
        if(CDMSds.dataType == 'DatacatQuery'):
            raise ValueError(
                'Cannot commit dataset with type "DatacatQuery", invalid type')
        try:
            path = corrPathCDMS(CDMSds.relativePath)
            if(not self.client.exists(path)):
                self.mkdir(path, parents=True)
            DSexists = self.client.exists(path+'/'+CDMSds.datasetName)
            if(DSexists):
                if(replace):
                    print('Replacing existing dataset:', path, '/',
                          CDMSds.datasetName)
                    self.rm(path+'/'+CDMSds.datasetName)
                else:
                    print('Skipping existing dataset:', path, '/',
                          CDMSds.datasetName)

            if(not DSexists or replace):
                self.client.mkds(path,
                                 CDMSds.datasetName,
                                 CDMSds.fileType,
                                 CDMSds.fileFormat,
                                 versionMetadata=CDMSds.metadata,
                                 resource=CDMSds.filePath,
                                 site=CDMSds.site)
        except Exception as e:
            if catch_errors:
                print(e)
                print("Could not create dataset")
            else:
                raise

    def fetch(self, *args, **kwargs):
        """ fetch (download) data, see fetch.py for arguments"""
        return fetchdata(self)
