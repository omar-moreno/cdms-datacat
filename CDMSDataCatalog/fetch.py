""" Utility functions for downloading data to local disk
"""

import pathlib
from concurrent.futures import ThreadPoolExecutor
import urllib
import shutil
import os
import requests
import subprocess
import sys
import logging
from tqdm import tqdm
from tqdm.utils import CallbackIOWrapper
from .CDMSDataset import CDMSDataset
import boto3
#from OSNTools import OSNTools

log = logging.getLogger(__name__)

class CDMSFetchError(CDMSDataset):
    """ Class to report information about fetch errors that may not result in
    sensible datasets.
    Args:
        request: The original request (usually a string) that caused the error
        fetchError (str): Description of the error
    """
    def __init__(self, request, error):
        super().__init__(None, None, None, None, None)
        self.fetchRequest = request
        self.fetchError = error

    def __str__(self):
        return self.fetchRequest

    def __repr__(self):
        return '<CDMSFetchError Class,'+self.fetchError+'>'

def get_default_fetchdir():
    """ Try to determine a default location for datacatalog data by inspecting
        paths that are present on the system.
    """
    # first look for official tier 1/2 locations
    # todo: do this by hostname!
    testpaths = ['/sdf/group/supercdms/data', 		#SLAC
                 '/scratch/m/mdiamond/mdiamond/data',   #Niagara
                 '/scratch/group/mitchcomp/CDMS/data',  #TAMU HPRC
                 '/scratch/group/cdms/data',            #ManeFrame
                 '/cvmfs/data',                         #XSEDE
                 '/data1/public_overflow/data',         #cdmsz3.fnal.gov
                 '/project/rrg-mdiamond/data',          #Cedar
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
        if fp and os.path.isfile(fp):
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
         open(target, 'wb') as fout:
        if progcallback:
            fout = CallbackIOWrapper(progcallback, fout, "write")
        shutil.copyfileobj(req.raw, fout)


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


def download_OSN(dataset, target, progcallback = None, endpointurl = None, bucketname = None, osn_access_key = None, osn_secret_key = None):
    """ Download a single dataset over rsync
    Args:
        dataset (CDMSDataset): the dataset (file) to download
        target (str): path and filename to save as
        access_key (str): the access key to the open storage network, the default is OSN_ACCESS_KEY
        secret_key (str): the secret key to the open storage network, the default is OSN_SECRET_KEY
    Returns:
        target (str): The target filepath of the file downloaded from the OSN
    """
    # Set default arguments
    endpointurl = 'https://ncsa.osn.xsede.org'
    bucketname = 'supercdms-data'

    # Get OSN keys
    osn_access_key = os.environ.get('OSN_ACCESS_KEY')
    osn_secret_key = os.environ.get('OSN_SECRET_KEY')

    
    # More set up (this requires you to import boto3)
    AWSClient = boto3.client('s3', aws_access_key_id=osn_access_key,
                                aws_secret_access_key=osn_secret_key,
                                endpoint_url = endpointurl)
    
    with open(target, 'wb') as fout:
        if progcallback:
            fout = CallbackIOWrapper(progcallback, fout, "write")
        # Download the specified file
        ############## Portion to fix
        # Option 1: Assume all dataset.relativePath from data registered on the DataCatalog the have a leading "/"
        AWSClient.download_fileobj(bucketname, dataset.relativePath[1:], fout)

        # Option 2: Not making the assumption made in "Option 1", while also preserving the dataset.relativePath property
        #if dataset.relativePath[0] == "/":
        #    AWSClient.download_fileobj(bucketname, dataset.relativePath[1:], fout)
        #else:
        #    AWSClient.download_fileobj(bucketname, dataset.relativePath, fout)
        ##############
    return target

def fetchdata(catalog, path, checkonly=None, dest=None, destRelative=True, 
              maxthreads=None, force=False):
    """Download a copy of the files pointed by path to the local system, only
    if it is not already found.

    Args:
      catalog: a CDMSDataCatalog object
      path:  The file(s) to copy. Can take many forms:
      
        * a single string giving the full data catalog entry path
        * a CDMSDataset
        * a string containing a wildcard '*', treated as a search query
        * a CDMSDataGroup (or path pointing to): download all ref'd todo
        * a list/tuple of paths/queries/Datasets


      checkonly (bool or int): if True, don't download, only look for datasets
                            already present on disk.  If False, download all
                            requested files without prompting. If a number,
                            ask for user confirmation if download is greater
                            than N MB. If None (default), use 100 MB
    
      dest (str or pathlib.Path): target directory to place the file in.
                          Missing directories will be created. File
                          will have same name as data catalog entry

      destRelative (bool): If True (default), create a directory
                           hierarchy under `destination` to match
                           the `relativePath` member. If `path` has
                           multiple entries, will be treated as True

      maxthreads (int): If a `path` expands to more than a single dataset, use
                        up to `maxthreads` simultaneous download connections
      force (bool): If True and a file is found but is bad (usually has wrong
                    size due to a cancelled download), delete the original 
                    and attempt to download again
    Returns:
      list: A flat list of CDMSDataset objects retrieved. The `filePath`
            attribute on each object will be set to the found/downloaded file
            if successful.
            Otherwise, `filePath` will be `None` and `fetchError` will contain
            more info about the error.
    """

    # sanity guard
    if not path:
        return CDMSFetchError(path, error="Empty request")

    if checkonly is None:
        checkonly = 100

    # check destination
    if dest is None:
        dest = catalog.default_fetchdir

    # at most complex, `path` could be a list of queries that will each expand
    # to lists of their own. First step is to flatten everything into a single
    # list of datasets to check and/or download
    tocheck = []
    errors = []
    
    def _expand_query(request):
        if isinstance(request, str):
            if request.find('*') != -1:
                # this is a search string, will return a list of datasets
                err = ""
                try:
                    datasets = catalog.search(request)
                except BaseException as e:
                    err = f"Error searching catalog: {e}"
                    errors.append(CDMSFetchError(request, err))
                else:
                    if datasets:
                        tocheck.extend(datasets)
                    else:
                        err = f"Search query yielded 0 results"
                        errors.append(CDMSFetchError(request, err))
            else:
                # this should be a full entry path
                try:
                    tocheck.append(catalog.get(request))
                except BaseException as e:
                    emsg = f"Error getting entry {request} from catalog: {e}"
                    err = CDMSFetchError(request, emsg)
                    err.relativePath = request
                    errors.append(err)
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

    allresults = tocheck + errors
    todownload = []

    success = []

    # now that we have a flat list of `CDMSDataset`s, check each one
    def _check_local(dataset, errifnotfound):
        target = get_fetch_path(dataset, dest, destRelative)
        if target:
            targetexists = os.path.isfile(target)
            if targetexists:
                size = os.path.getsize(target)
                if dataset.size and size != dataset.size:
                    if force and not errifnotfound:
                        todownload.append(dataset)
                    else:
                        dataset.fetchError = f"File '{target}' size mismatch"
                        errors.append(dataset)
                else:
                    dataset.filePath = target
                    success.append(dataset)
            else:
                if errifnotfound:
                    dataset.fetchError = f"File '{target}' not found on disk"
                    errors.append(dataset)
                else:
                    todownload.append(dataset)
        else:
            dataset.fetchError = "Unable to determine local disk path"
            errors.append(dataset)
                    
        
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

            pbar.abort = False
            def _callback(n=1):
                """wrap tqdm.update with the ability to abort"""
                if pbar.abort:
                    raise pbar.abort
                pbar.update(n)

            def _get(dataset):
                try:
                    #fail fast in case we've gotten an abort request
                    _callback(0)
                    target = get_fetch_path(dataset, dest, destRelative)
                    # we need to actually do the download
                    targetDir = os.path.dirname(target)
                    pathlib.Path(targetDir).mkdir(parents=True, exist_ok=True)
                    if dataset.site == 'OSN':
                        download_OSN(dataset, target, _callback)
                    elif dataset.site == 'SLAC':
                        download_web(dataset, target, baseurl, _callback)

                except BaseException as e:
                    dataset.fetchError = f"Exception during download: {e}"
                return dataset
            
            pool = ThreadPoolExecutor(max_workers=maxthreads)
            dls = pool.map(_get, todownload)
            try:
                pool.shutdown()
            except KeyboardInterrupt as e:
                print("Aborting download...")
                pbar.abort = KeyboardInterrupt("User interrupted")
            for dl in dls:
                if dl.fetchError:
                    errors.append(dl)
                else:
                    _check_local(dl, errifnotfound=True)
        
        tqdm.write("Download finished")

    elif todownload:
        print("Skipping download")
        for dataset in todownload:
            dataset.fetchError = 'Download prevented'
            errors.append(dataset)

    # we're finally done!
    if errors:
        log.warn(f"DataCat WARNING: Failed to fetch {len(errors)}/{len(allresults)} datasets!")
        #for err in errors:
            #warn(f"\t{str(err)}: {err.fetchError}")
    return allresults
    
