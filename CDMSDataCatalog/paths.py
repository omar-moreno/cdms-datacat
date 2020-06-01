""" Utility functions to generate and interpret data catalog entry paths
"""
from warnings import warn

def fridgeRun_tostring(fridgeRun):
    """ Convert the argument to the form 'R<n\>' """
    result = str(fridgeRun)
    if result != '*' and not result.startswith('R'):
        result = 'R'+result
    return result


def getpath_rawdata(Facility, nFridgeRun, Series=None, filename=None):
    """ Get the data catalog entry path for raw data """
    fridgeRun = fridgeRun_tostring(nFridgeRun)
    path = '/'.join(('/CDMS', Facility, fridgeRun, 'Raw'))
    if Series:
        path = '/'.join((path, str(Series)))
        if filename:
            path = '/'.join((path, filename))
    return path
        

def getpath_processed(Facility, nFridgeRun, ProdType, ProdTag, nMergeLevel=None,
                      Series=None, ProdStep=None, filename=None):
    """ Get the data catalog entry path for processed data """
    fridgeRun = fridgeRun_tostring(nFridgeRun)

    # this handles ProdType is '*'
    prodPath = 'Processed/'+ProdType
    if ProdType == 'test':
        prodPath = 'Processed/Tests'
    elif ProdType == 'release': 
        prodPath = 'Processed/Releases'
    path = '/'.join(('/CDMS', Facility, fridgeRun, prodPath, ProdTag))
    
    mergepath = nMergeLevel
    if ProdStep == 'BatNoise':
        mergepath = 'Noise'
    elif ProdStep == 'Cut':
        mergepath = 'Cuts'
    elif isinstance(nMergeLevel, int):
        mergepath = {0: 'Unmerged', 
                     1: 'Submerged', 
                     2: 'Merged'} [nMergeLevel]
    if mergepath is not None:
        path = '/'.join((path, mergepath))
    
    if Series is not None:
        if mergepath == 'Unmerged':
            path = '/'.join((path, str(Series)))
        else:
            #warn(f"Series argument ignored for nMergeLevel={nMergeLevel}")
            pass

    if filename is not None:
        path = '/'.join((path, filename))

    return path


def getpath_data(Facility, nFridgeRun, ProdType, ProdTag=None, nMergeLevel=None,
                 Series=None, ProdStep=None, filename=None):
    """ Get the data catalog entry path for either raw or processed data,
    depending on the `ProdType` argument.
    """
    path = None
    if ProdType is None or ProdType.lower() == 'raw':
        # consistency check
        #if ProdTag:
            #warn("Ignoring ProdTag for 'raw' processing type")
        #if nMergeLevel:
            #warn("Ignoring nMergeLevel for 'raw' processing type")
        path = getpath_rawdata(Facility, nFridgeRun, Series, filename)
       
    elif ProdType.lower() in ('test', 'release', '*'):
        path = getpath_processed(Facility, nFridgeRun, ProdType, ProdTag,
                                 nMergeLevel, Series, ProdStep, filename)
    else:
        raise ValueError(f"Unknown value '{ProdType}' for ProdType,\n"
                         "Should be one of 'raw', 'test', 'release'")
    return path


def is_simple_arg(val, allowstar=True, allownone=True):
    """ Determine whether `val` is a single, specific argument for constructing
    a data catalog path or has some kind of wildcard.
    Args:
        val: the path component to interpret, usually a str
        allowstar (bool): if True (default), let `*` count as a simple argument
                          (i.e. accept all values for that path level)
        allownone (bool): If True (default) let `None` count as a simple argument
    Returns:
        bool: Is the argument a basic (non-wildcard) argument?
     """
    if val == '*':
        return allowstar
    elif val is None:
        return allownone
    elif (isinstance(val, str) and (val.find('*') != -1 or
                                    val.find('[') != -1)    ):
        return False
    return isinstance(val, (str, int, float))
        

def build_query_phrase(key, val):
        """ interpret `val` as a DataCatalog language filter on `key`. 
        Allowed types are:
        
        - str: plain strings generate 'eq' queries. Strings containing wildcards
               (*, []) generate =~ queries
        - list, tuple: generate 'in' queries
        - slice: generate range queries (step is ignored)
        - int or float generate 'eq' queries
        """
        def escapestr(s, convertbool=True):
            if isinstance(s, str):
                s = f"'{s}'"
            elif convertbool and isinstance(s, bool):
                s = int(s)
            return s

        op = 'eq'
        suffix = escapestr(val)

        if isinstance(val, slice):
            op = 'in'
            suffix = f"{escapestr(val.start)}:{escapestr(val.stop)}"
        
        elif isinstance(val, (list, tuple)):
            op = 'in'
            suffix = tuple(val)

        elif isinstance(val, str):
            if val.find('*') != -1 or val.find('[') != -1:
                op = '=~'
                
        return f"{key} {op} {suffix}"

def build_query(basequery=None, **kwargs):
    """ Build a single query string from a list of arguments """
    if basequery is not None:
        basequery = [basequery]
    return ' and '.join(build_query_phrase(k, v) for k, v in kwargs.items)
