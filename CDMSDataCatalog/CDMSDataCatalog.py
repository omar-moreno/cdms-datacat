import datacat
from datacat import client_from_config, config_from_file
import pathlib
import pkg_resources

from .fetch import fetchdata, get_default_fetchdir
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
    def __init__(self, config_file=None, default_fetchdir=None):
        """ Create a new Data Catalog client.
        The file specified by `config_file` can contain the following:
        
        url: base URL for accessing the catalog web interface
        auth_type: web authentication standard
        auth_key_id: authentication id
        auth_secret_key: authentication public key
        default_fetchdir: sroot directory for fetching (downloading) data

        Args:
            config_file (str): location of config file with client settings
            default_fetchdir (str): same as default_fetchdir config variable
        """
        
        # load the configuration file
        if config_file is None:
            config_file = pkg_resources.resource_filename(__name__,
                                                          'cfg/default.cfg')
        config = config_from_file(config_file)

        # determine default data fetchdir
        self.default_fetchdir = default_fetchdir
        if default_fetchdir is None:
            self.default_fetchdir = get_default_fetchdir()
            # see if it was specified in the config file
            try:
                self.default_fetchdir = config['defaults']['default_fetchdir']
            except KeyError: # this is not in the config file
                pass
        
        self.client = client_from_config(config)
        
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

    def search(self, path, site='All',  **kwargs):
        path = corrPathCDMS(path)
        results = self.client.search(path, site=site, **kwargs)
        # results come back unsorted, which is not what we want
        results.sort(key=lambda res: res.path)
        return list(CDMSDataset.fromDataset(res) for res in results)

    def get(self, path, site='All'):
        """Convert a path (string) to a full CDMSDataset object"""
        path = corrPathCDMS(path)
        rawds = self.client.path(path, site=site)
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
        return fetchdata(self, *args, **kwargs)
