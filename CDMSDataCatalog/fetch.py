import pathlib
from concurrent.futures import ThreadPoolExecutor
import urllib
import shutil
import os
import requests
import subprocess
from tqdm.auto import tqdm
from tqdm.utils import CallbackIOWrapper
from .CDMSDataset import CDMSDataset


def get_default_fetchdir():
    """ Try to determine a default location for datacatalog data by inspecting
        paths that are present on the system.
    """
    # first look for official tier 1 locations
    # todo: do this by hostname!
    testpaths = ['/nfs/slac/g/supercdms/data', #SLAC
                 '/data1/public_overflow/datacat-data', #cdmsz3.fnal.gov
                ]
    for path in testpaths:
        if os.path.isdir(path):
            return path

    # see if there is a scratch directory, mostly for grid nodes
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
        target = dest or get_default_fetchdir()
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

    def __init__(self, request, filepath=None, error=None):
        self.request = request
        try:
            self.filepath = os.path.abspath(filepath)
        except TypeError:
            self.filepath = filepath
        self.error = error
        self.success = (error is None)

    def summary(self):
        if self.success:
            print("Fetch", self.request, "succeeded. File at", self.filepath)
        else:
            print("\x1b[1;31mFetch", self.request, "failed\x1b[0m", self.error)

    def __bool__(self):
        return self.success

    def __repr__(self):
        return "CDMSFetchRequest(%s)" % ("success" if self.success
                                         else "failed: %s" % self.error)

    def __str__(self):
        return repr(self)

    # for easier compatibility with MultiFetchRequest:
    def __iter__(self):
        return [self].__iter__()

    @property
    def filepaths(self):
        return [self.filepath]

    @property
    def valid_filepaths(self):
        return self.filepaths


class CDMSMultiFetchResult(object):
    """Container for multiple fetch requests"""
    def __init__(self, request, results):
        self.request = request
        self.results = results

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

    def __bool__(self):
        return self.success

    @property
    def filepaths(self):
        """ Return a list of local disk paths for this request.
        Raises: ValueError if any request had an error
        """
        if not self.success:
            raise ValueError("Some fetch results returned errors")
        return [res.filepath for res in results]

    @property
    def valid_filepaths(self):
        """ Return a list of all *valid* local disk paths for successful
        requests. will not throw
        """
        return [res.filepath for res in results if res]

    def __repr__(self):
        succeeded = sum(1 for res in self.results if res)
        return f"CDMSMultFetchRequest({request}, {succeeded}/{len(self)} succeeded)"

    def __str__(self):
        return repr(self)

def print_filesize(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def download_web(dataset, target, baseurl, progcallback=None):
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
    with requests.get(url, params=params, stream=True) as req, \
         open(target, 'wb') as fout, \
         tqdm(total=dataset.size, unit='B', unit_scale=True, unit_divisor=1024,
              desc=os.path.basename(target), leave=False,
              disable=dataset.size<5000000) as progbar :
        def update(size):
            progbar.update(size)
            if progcallback:
                progcallback(size)
        shutil.copyfileobj(req.raw, CallbackIOWrapper(update, fout, "write"))


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

def fetchdata(catalog, path, checkonly=None, dest=None, destRelative=True, 
              maxthreads=None):
    """Download a copy of the files pointed by path to the local system, only
    if it is not already found.

    Args:
      catalog: a CDMSDataCatalog object
      path:  The file(s) to copy. Can take many forms:
             - a single string giving the full data catalog entry path
             - a CDMSDataset
             - a string containing a wildcard '*', treated as a search query
             - a CDMSDataGroup (or path pointing to): download all ref'd todo
             - a list/tuple of paths/queries/Datasets

      checkonly (bool/int): if True, don't download, only look for datasets
                            already present on disk.  If False, download all
                            requested files without prompting. If a number,
                            ask for user confirmation if download is greater
                            than N MB. If None (default), use 100 MB
    
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
                       Also update the `filepath` member to new location.
                       Else returns F, though in many cases an exception
                       will be raised first.
    """

    # sanity guard
    if not path:
        return CDMSFetchResult(path, error="Empty request")

    if checkonly is None:
        checkonly = 100

    # check destination
    if dest is None:
        dest = catalog.default_fetchdir

    # at most complex, `path` could be a list of queries that will each expand
    # to lists of their own. First step is to flatten everything into a single
    # list of datasets to check and/or download
    tocheck = []
    todownload = []
    errors = []
    success = []
    def _expand_query(request):
        if isinstance(request, str):
            if request.find('*') != -1:
                # this is a search string, will return a list of datasets
                err = ""
                try:
                    datasets = catalog.search(request)
                except BaseException as e:
                    err = f"Error searching catalog: {e}"
                    errors.append(CDMSFetchResult(request, error=err))
                else:
                    if datasets:
                        tocheck.extend(datasets)
                    else:
                        err = f"Search query yielded 0 results"
                        errors.append(CDMSFetchResult(request, error=err))
            else:
                # this should be a full entry path
                try:
                    tocheck.append(catalog.get(request))
                except BaseException as e:
                    err = f"Error getting entry from catalog: {e}"
                    errors.append(CDMSFetchResult(requeset, error=err))
        elif isinstance(request, CDMSDataset):
            tocheck.append(request)
        else:
            # request should be a loop
            try:
                for req in request:
                    _expand_query(req)
            except TypeError:
                raise TypeError(f"Unhandled type {type(request)} for fetch")

    _expand_query(path)

    # now that we have a flat list of `CDMSDataset`s, check each one
    def _check_local(dataset, errifnotfound):
        target = get_fetch_path(dataset, dest, destRelative)
        if target:
            targetexists = os.path.isfile(target)
            if targetexists:
                size = os.path.getsize(target)
                if dataset.size and size != dataset.size:
                    err = "File size mismatch"
                    errors.append(CDMSFetchResult(dataset, error=err))
                else:
                    success.append(CDMSFetchResult(dataset, filepath=target))
            else:
                if errifnotfound:
                    err = "File not found on local disk"
                    errors.append(CDMSFetchResult(dataset, error=err))
                else:
                    todownload.append(dataset)
        else:
            err = "Unable to determine local disk path"
            errors.append(CDMSFetchResult(dataset, error=err))
                    
        
    for dataset in tocheck:
        _check_local(dataset, errifnotfound=False)
    tocheck = []

    # now download any required files
    # TODO: should we skip download if there are errors already?
    dlsize = sum(dataset.size for dataset in todownload)
    dodownload = checkonly is not True and dlsize > 0
    if dlsize > 0:
        print("Need to download", print_filesize(dlsize),
              "(", len(todownload), "files ) from catalog")
        if checkonly is not True and dlsize > checkonly*1000000:
            confirm = input("Do you want to proceed? (y/n): ")
            dodownload = confirm[0] in 'Yy'

    if dodownload:
        baseurl = catalog.client.http_client.base_url
        # tqdm gives nice progress bars
        with tqdm(total=dlsize, desc="Total progress", position=0, unit='B',
                  unit_scale=True, unit_divisor=1024) as pbar:
            def _get(dataset):
                target = get_fetch_path(dataset, dest, destRelative)
                # we need to actually do the download
                targetDir = os.path.dirname(target)
                try:
                    pathlib.Path(targetDir).mkdir(parents=True, exist_ok=True)
                    download_web(dataset, target, baseurl, pbar.update)
                except BaseException as e:
                    err = f"Exception during download: {e}"
                    errors.append(CDMSFetchResult(dataset, error=err))
                else:
                    _check_local(dataset, errifnotfound=True)
                    
            with ThreadPoolExecutor(max_workers=maxthreads) as pool:
                pool.map(_get, todownload)
        tqdm.write("Download finished")
    elif todownload:
        print("Skipping download")
        for dataset in todownload:
            errors.append(CDMSFetchResult(dataset, error="Download prevented"))

    # we're finally done!
    return CDMSMultiFetchResult(path, success + errors)
    
