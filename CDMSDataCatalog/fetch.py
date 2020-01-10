from .CDMSDataset import CDMSDataset
import pathlib
from multiprocessing.pool import ThreadPool
import urllib
import shutil
import os
import requests


class CDMSFetchResult(object):
    """An instance of this class is returned by `fetch` operations.
    It is truthy if all fetches completed successfully. Details on each
    individual request are provided.
    """

    def __init__(self, request, success, filePath=None, error=None):
        self.request = request
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
                                         else "failed")

    def __str__(self):
        return repr(self)


class CDMSMultiFetchResult(CDMSFetchResult):
    """Container for multiple fetch requests"""
    def __init__(self, results):
        self.request = results
        self.filePath = None

    def summary(self):
        if self.success:
            print("All", len(self.request), "fetches succeeded")
        else:
            succeeded = sum(1 for req in self.request if req)
            print(succeeded, "out of", len(self.request), "succeeded")
            for req in self.request:
                req.summary()

    def __getitem__(self, key):
        return self.request[key]

    def __iter__(self):
        return self.request.__iter__()

    @property
    def success(self):
        return all(self.request)

    @success.setter
    def success(self, val):
        pass

    @property
    def error(self):
        return {res.request: res.error for res in self.request if not res}

    @error.setter
    def error(self, val):
        pass


def fetchdata(catalog, path, dest=None, destRelative=True, force=False,
              maxthreads=None):
    """Download a copy of the files pointed by path to the local system.
    Args:
      catalog: a CDMSDataCatalog object
      path:  The file(s) to copy. Can take many forms:
             - a single string giving the full data catalog entry path
             - a CDMSDataset
             - a CDMSDataGroup (or path pointing to): download all ref'd
             - a list/tuple of paths/Datasets

      dest (str or Path): target directory to place the file in.
                          Missing directories will be created. File
                          will have same name as data catalog entry
      destRelative (bool): If True (default), create a directory
                           hierarchy under `destimation` to match
                           the `relativePath` member. If `path` has
                           multiple entries, will be treated as True
      force (bool): If True, overwrite an existing file at the destination.
                    If False (default), return failure if existing file
                    doesn't match datacat entry.
      maxthreads (int): If a list, use up to `maxthreads` simultaneous
                        download connections
    Returns:
      CDMSFetchResult: If file was successfully downloaded / already exists
                       and passes size or checksum verification, return T.
                       Also update the `filePath` member to new location.
                       Else returns F, though in many cases an exception
                       will be raised first.
    """
    # check destination
    if dest is None:
        dest = catalog.defaultDataRoot

    # first check the type of path
    if isinstance(path, (list, tuple)):
        # fetch each one individually (in multiple threads), return the set
        if maxthreads is not None:
            maxthreads = min(maxthreads, len(path))
        with ThreadPool(processes=maxthreads) as pool:
            def dofetch(apath):
                return fetchdata(catalog, apath, dest, destRelative, force)
            return CDMSMultiFetchResult(pool.map(dofetch, path))

    elif isinstance(path, str):
        # convert to a Dataset
        try:
            path = catalog.get(path)
        except BaseException as e:
            return CDMSFetchResult(path, success=False, error=str(e))

    # if we get here, path _should_ be a CDMSDataset
    dataset = path
    if not isinstance(dataset, CDMSDataset):
        error = f"Unhandled type '{type(path)}' for `path` argument"
        return CDMSFetchResult(path, success=False, error=error)

    # need low-level dataset items later
    # rawds = getattr(dataset, 'rawDataset', None)
    # filesize = getattr(rawds, 'size', rawds.locations[0].size)

    # figure out the full destination path/filename
    target = dest
    if destRelative:
        relPath = dataset.relativePath
        if os.path.isabs(relPath):
            relPath = relPath[1:]
        target = os.path.join(target, relPath)
    else:
        target = os.path.join(target, dataset.datasetName)

    targetexists = os.path.isfile(target)
    if force or not targetexists:
        # we need to actually do the download
        targetDir = os.path.dirname(target)
        try:
            pathlib.Path(targetDir).mkdir(parents=True, exist_ok=True)
        except BaseException as e:
            error = "Unable to create target directory {}: {}"
            error = error.format(targetDir, e)
            return CDMSFetchResult(path, success=False, error=error)

        # determine the URL for the file
        baseparsed = urllib.parse.urlparse(catalog.client.http_client.base_url)
        url = urllib.parse.urlunparse((baseparsed[0], baseparsed[1],
                                       'DataCatalog/get', '', '', ''))
        # need to get raw dataset to determine url
        locationPk = dataset.locationPk
        if locationPk is None:
            return CDMSFetchResult(path, success=False,
                                   error="Unable to generate download URL")
        params = dict(datasetLocation=locationPk)
        # finally we can download to file
        # from https://stackoverflow.com/questions/16694907/
        mb = dataset.size/1024/1024 if dataset.size else "unknown"
        print("Downloading file", dataset.datasetName, "%.2f" % mb, "MB")
        # what about auth?
        with requests.get(url, params=params, stream=True) as req:
            with open(target, 'wb') as f:
                shutil.copyfileobj(req.raw, f)
        print("Finished downloading", dataset.datasetName)

    # now make sure the local file matches size
    try:
        size = os.path.getsize(target)
    except OSError as e:
        return CDMSFetchResult(path, success=False, filePath=target,
                               error="File not downloaded: {}".format(e))
    if dataset.size is not None and size != dataset.size:
        return CDMSFetchResult(path, success=False, filePath=target,
                               error="File size does not match")

    # finally we are successful!
    return CDMSFetchResult(path, success=True, filePath=target)
