import pathlib
from multiprocessing.pool import ThreadPool
import urllib
import shutil
import os
import requests
import subprocess


def get_default_fetchdir():
    """ Try to determine a default location for datacatalog data by inspecting
        paths that are present on the system.
    """
    # first look for official tier 1 location
    slacpath = '/nfs/slac/g/supercdms/data'
    if os.path.isdir(slacpath):
        return slacpath

    # see if there is a scratch directory
    if os.path.isdir('/scratch'):
        return '/scratch/CDMS/datacat-data'

    # just make everything relative to CWD
    return 'datacat-data'

def get_fetch_path(dataset, dest=None, destRelative=True):
    """ Get the location where this file would be downloaded to
    Args:
        dataset: The CDMSDataset to check
        dest (str): top-level destination directory
        destRelative (bool): if True, recreate the datacat path below dest
    """
    if dest is None:
        dest = get_default_fetchdir()
    # first, see if it's sitting at one of the official paths
    target = None
    targetexists = False
    for fp in dataset.getSitePaths().values():
        if os.path.isfile(fp):
            target = fp
            targetexists = True
            break

    if not targetexists:
        # build the path for fetching relative to dest
        target = dest
        if destRelative:
            relPath = dataset.relativePath
            if os.path.isabs(relPath):
                relPath = relPath[1:]
            target = os.path.join(target, relPath)
        else:
            target = os.path.join(target, dataset.datasetName)
    return target

class CDMSFetchResult(object):
    """An instance of this class is returned by `fetch` operations.
    It is truthy if all fetches completed successfully. Details on each
    individual request are provided.
    """

    def __init__(self, request, success, filePath=None, error=None):
        self.request = request
        try:
            self.filePath = os.path.abspath(filePath)
        except TypeError:
            self.filePath = filePath
        self.success = success
        self.error = error

    def summary(self):
        if self.success:
            print("Fetch", self.request, "succeeded. File at", self.filePath)
        else:
            print("\x1b[1;31mFetch", self.request, "failed\x1b[0m", self.error)

    def __bool__(self):
        return self.success

    def __repr__(self):
        return "CDMSFetchRequest(%s)" % ("success" if self.success
                                         else "failed: %s" % self.error)

    def __str__(self):
        return repr(self)

    def __iter__(self):
        return [self].__iter__()


class CDMSMultiFetchResult(CDMSFetchResult):
    """Container for multiple fetch requests"""
    def __init__(self, results):
        self.results = results
        self.request = [res.request for res in results]
        self.filePath = [res.filePath for res in results]

    def summary(self, verbose=True):
        if self.success:
            print("All", len(self.results), "fetches succeeded")
        else:
            succeeded = sum(1 for res in self.results if res)
            print(succeeded, "out of", len(self.results), "succeeded")
            if verbose:
                for res in self.results:
                    res.summary()

    def __getitem__(self, key):
        return self.results[key]

    def __iter__(self):
        return self.results.__iter__()

    def __len__(self):
        return len(self.results)

    @property
    def success(self):
        return all(self.results)

    @success.setter
    def success(self, val):
        pass

    @property
    def error(self):
        return {res.request: res.error for res in self.results if not res}

    @error.setter
    def error(self, val):
        pass

    def __repr__(self):
        succeeded = sum(1 for res in self.results if res)
        return f"CDMSMultFetchRequest({succeeded}/{len(self)} succeeded)"


def download_web(dataset, target, baseurl):
    """ Download a file through the data catalog web interface
    Args:
        dataset (CDMSDataset): the datsaet to download
        target (str): path and name to download the file as
        baseurl (str): the root URL of the data catalog interface
    Raises:
        AttributeError if unable to determine  full URL from dataset
    """
    # determine the URL for the file
    baseparsed = urllib.parse.urlparse(baseurl)
    url = urllib.parse.urlunparse((baseparsed[0], baseparsed[1],
                                   'DataCatalog/get', '', '', ''))
    # need to get raw dataset to determine url
    locationPk = dataset.locationPk
    if locationPk is None:
        raise AttributeError("Unable to generate download URL")

    params = dict(datasetLocation=locationPk)
    # finally we can download to file
    # from https://stackoverflow.com/questions/16694907/
    # what about auth?
    with requests.get(url, params=params, stream=True) as req:
        with open(target, 'wb') as f:
            shutil.copyfileobj(req.raw, f)


def download_rsync(dataset, target, host='centos7.slac.stanford.edu'):
    """ Download a single dataset over rsync
    Args:
        dataset (CDMSDataset): the dataset (file) to download
        target (str): path and filename to save as
        host (str): the host to rsync (ssh) to
    Returns:
        subprocess.run result
    Raises:
        AttributeError if unable to determine source data path
    """
    sourcepath = dataset.findLocation('SLAC').resource
    sourceurl = host + ":" + sourcepath
    return subprocess.run(['rsync', '-a', sourceurl, target])


def fetchdata(catalog, path, checkonly=False, dest=None, destRelative=True, 
              maxthreads=None):
    """Download a copy of the files pointed by path to the local system, only
    if it is not already found.

    Args:
      catalog: a CDMSDataCatalog object
      path:  The file(s) to copy. Can take many forms:
             - a single string giving the full data catalog entry path
             - a CDMSDataset
             - a CDMSDataGroup (or path pointing to): download all ref'd todo
             - a list/tuple of paths/Datasets

      checkonly (bool): if True, look to see if data is already present on 
                        disk and abort if not found
    
      dest (str or Path): target directory to place the file in.
                          Missing directories will be created. File
                          will have same name as data catalog entry
      destRelative (bool): If True (default), create a directory
                           hierarchy under `destimation` to match
                           the `relativePath` member. If `path` has
                           multiple entries, will be treated as True
      maxthreads (int): If a list, use up to `maxthreads` simultaneous
                        download connections
    Returns:
      CDMSFetchResult: If file was successfully downloaded / already exists
                       and passes size or checksum verification, return T.
                       Also update the `filePath` member to new location.
                       Else returns F, though in many cases an exception
                       will be raised first.
    """
    if not path:
        return CDMSFetchResult(path, success=False, error="Empty request")
    
    # check destination
    if dest is None:
        dest = catalog.default_fetchdir

    # first check the type of path
    if isinstance(path, (list, tuple)):
        # fetch each one individually (in multiple threads), return the set
        def dofetch(apath):
            return fetchdata(catalog, apath, checkonly, dest, destRelative)
        if maxthreads is not None:
            maxthreads = min(maxthreads, len(path))
        with ThreadPool(processes=maxthreads) as pool:
            try:
                results = pool.map(dofetch, path)
            except KeyboardInterrupt as e:
                print("\n******** Canceling download ******** \n")
                pool.terminate()
                pool.join()
                print("\nDownload cancelled")
                results = [CDMSFetchResult(pth, success=False,
                                           error='cancelled')
                           for pth in path]
            return CDMSMultiFetchResult(results)

    elif isinstance(path, str):
        if path.find('*') != -1:
            # this is a search string
            try:
                datasets = catalog.search(path)
            except BaseException as e:
                return CDMSFetchResult(path, success=False, error=str(e))
            return fetchdata(catalog, datasets, checkonly, dest, destRelative)
        # if we get here, it's a plain string, so convert to a Dataset
        try:
            path = catalog.get(path)
        except BaseException as e:
            return CDMSFetchResult(path, success=False, error=str(e))

    # if we get here, path _should_ be a CDMSDataset
    dataset = path
    target = get_fetch_path(dataset, dest, destRelative)
    if not target:
        return CDMSFetchResult(path, success=False,
                               error="Unable to determine fetch target path")

    targetexists = os.path.isfile(target)
    if not targetexists:
        if checkonly: # nothing to do but fail here
            return CDMSFetchResult(path, success=False,
                                   error="Checked target does not exist")


        # we need to actually do the download
        targetDir = os.path.dirname(target)
        try:
            pathlib.Path(targetDir).mkdir(parents=True, exist_ok=True)
        except BaseException as e:
            error = "Unable to create target directory {}: {}"
            error = error.format(targetDir, e)
            return CDMSFetchResult(path, success=False, error=error)

        # give a message with size
        sizestr = "unknown"
        if dataset.size:
            if dataset.size > 1024*1024*1024:
                sizestr = "%.2f GB" % (dataset.size/1024/1024/1024)
            elif dataset.size > 1024*1024:
                sizestr = "%.2f MB" % (dataset.size/1024/1024)
            else:
                sizestr = "%.2f kB" % (dataset.size/1024)
        print("Downloading file", dataset.datasetName, '(', sizestr, ')...')
        try:
            download_web(dataset, target, catalog.client.http_client.base_url)
        except AttributeError as e:
            return CDMSFetchResult(path, success=False, error=str(e))
        print("Finished downloading", dataset.datasetName)

    # now make sure the local file matches size
    try:
        size = os.path.getsize(target)
    except OSError as e:
        return CDMSFetchResult(path, success=False, filePath=target,
                               error="File not downloaded: {}".format(e))
    if dataset.size and size != dataset.size:
        return CDMSFetchResult(path, success=False, filePath=target,
                               error="File size does not match")

    # finally we are successful!
    return CDMSFetchResult(path, success=True, filePath=target)
