import datacat
from datacat import client_from_config, config_from_file
import pathlib
import pkg_resources
import logging

from .fetch import fetchdata, get_default_fetchdir
from .CDMSDataset import CDMSDataset
from . import paths

log = logging.getLogger(__name__)

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

    def search(self, path, site='All', getallmetadata=False, **kwargs):
        """ Call `client.search` and return sorted CDMSDatasets
        Normally search results don't contain metadata unless specified by the
        `show` optional argument.  if `getrallmetadata` is True, call `get` on
        each hit returned to get it's full metadata list.  This results in a
        separate round-trip query for each hit, so don't enable unless you
        need it; giving `show` is MUCH more efficient. 
        """
        path = corrPathCDMS(path)
        results = self.client.search(path, site=site, **kwargs)
        # results come back unsorted, which is not what we want
        results.sort(key=lambda res: res.path)
        if getallmetadata:
            results = [self.get(res.path, site=site) for res in results]
        else:
            results = [CDMSDataset.fromDataset(res) for res in results]
        return results

    def get(self, path, site='All'):
        """Convert a path (string) to a full CDMSDataset object"""
        path = corrPathCDMS(path)
        rawds = self.client.path(path, site=site)
        return CDMSDataset.fromDataset(rawds)

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


    def buildDataSearch(self, Facility='*', nFridgeRun='*', ProdType='*', 
                        ProdTag='*', nMergeLevel=None, Series='*', 
                        ProdStep=None, filename=None, query=None, **kwargs):
        """ Construct the data catalog path and query string for CDMS
        datasets. Arguments starting with a capital are generally directly
        equivalent to metadata arguments. 

        TODO: Convert data type string ('ba', cf', etc) to number
        """
        if query:
            query = [query]
        else:
            query = []

        # for each parameter, if it is a special query argument, replace
        # with '*' in the path
        def checksimple(param_, name_, query_):
            if not paths.is_simple_arg(param_):
                query.append(paths.build_query_phrase(name_, param_))
                return '*'
            return param_
        
        # handle special 'last' case for nFridgeRun
        if nFridgeRun == 'last' or nFridgeRun == -1:
            if not paths.is_simple_arg(Facility, allowstar=False,
                                       allownone=False):
                raise ValueError("Can't find last fridge run without facility")
            nFridgeRun = self.getLastFridgeRunNumber(Facility)

        Facility = checksimple(Facility, 'Facility', query)
        nFridgeRun = checksimple(nFridgeRun, 'nFridgeRun', query)
        ProdType = checksimple(ProdType, 'ProdType', query)
        ProdTag = checksimple(ProdTag, 'ProdTag', query)
        nMergeLevel = checksimple(nMergeLevel, 'nMergeLevel', query)
        Series = checksimple(Series, 'Series', query)
        ProdStep = checksimple(ProdStep, 'ProdStep', query)

        path = paths.getpath_data(Facility, nFridgeRun, ProdType, ProdTag, 
                                  nMergeLevel, Series, ProdStep, filename)
        if path.endswith('*') and not path.endswith('**'):
            path += '*'

        # handle additional query args from kwargs, convert to string
        # todo: handle nDataType here
        for k, v in kwargs.items():
            query.append(paths.build_query_phrase(k, v))
        query = ' and '.join(query)
        
        return path, query
        

    def findData(self, query=None, dofetch=False, fetchcheckonly=None, **kwargs):
        """ Run a query to find data against the data catalog
        Args:
          query (str):  The datacat client query (filter) to run. Can be blank,
                        in which case it will be entirely built from kwargs. 
          dofetch (bool): If True, call fetch on all the result data (i.e.,
                          find the corresponding files on local disk)
          fetchcheckonly (bool): If True, only check for local files, but
                                 don't download if missing.  Ignored if
                                 `dofetch` is False.
          **kwargs:  Additional keyword arguments are interpreted as metadata
                     query parameters

        Output: data
          if `dofetch` is False, data is a list of `CDMSDataset` objects.
          Otherwise, data is a `CDMSMultiFetchRequest`. 
          
        """
        site = kwargs.pop('site', 'All')
        path, query = self.buildDataSearch(**kwargs)
        # should we catch exceptions here, or let them bubble?
        log.debug("Searching path %s with additional query '%s'", path, query)
        datasets = self.search(path, site=site, query=query)
        if dofetch:
            datasets = self.fetch(datasets, checkonly=fetchcheckonly)
        return datasets
  

    def getProductionInfo(self,facility='',fridgeRun='', processingType = '', productionTagList=[],verbose=True):
        """ Get production tag list and metadata

        Args:
           facility = 'CUTE', 'SLAC', 'NEXUS', etc.   (required)
           fridgeRun = 10, 11, etc  OR 'last (required)
           processingType= 'release' or 'test' (default: 'release')
           productionTagList = list of production tag such as Prodv9.5.3' (default: return all tags)
           verbose = True/False (default: True)

        Output: dictionary
        """
        # check arguments    
        if not facility or not fridgeRun:
            print('Required arguments: "facility" and "fridgeRun"')
            return

     
        if not processingType:
            if verbose:
                print('No "processingType" provided. Will use "release"!')
            processingType = 'release'


        output_dict = dict()
        
        # ====================
        # Build path
        # ====================

        # fridge run
        run_name = str(fridgeRun)
        if run_name=='last':
            run_number = self.getLastFridgeRunNumber(facility)
            if run_number == -999999:
                print('ERROR: unable to find last fridge run number!')
                return
            run_name = 'R' + str(run_number)
            if verbose:
                print('Last Run: ' + run_name)
        elif run_name[0]!='R':
            run_name = 'R' + str(fridgeRun)
            
        
        datacatalog_path = '/CDMS/' + facility + '/' + run_name  +'/Processed/'
        if processingType == 'release':
            datacatalog_path  =  datacatalog_path  + 'Releases'
        elif processingType == 'test':
            datacatalog_path  =  datacatalog_path  + 'Tests'
        else:
            print('ERROR: processingType should be either "release" or "test"')
            return output_dict

        # ====================
        # Get tags
        # ====================

        try:
            folder_list  = self.client.children(datacatalog_path)
        except:
            print('ERROR: Problem reading datacatalog path: ' +  datacatalog_path)
            return output_dict

        for datacat_folder in folder_list:
           
            # get metadata
            prod_tag = datacat_folder.name

            # filter
            if productionTagList:
                if prod_tag not in productionTagList:
                    continue

            folder_metadata = dict()
            if (hasattr(datacat_folder,'metadata')):
                folder_metadata= dict(datacat_folder.metadata)
                
            # output
            output_dict[prod_tag] = folder_metadata
            
            
            
        return  output_dict



    def getSeriesInfo(self,facility='',fridgeRun='', seriesList=[], isInSLAC=True, 
                      dataTypeList=[], beginDateTime=[],endDateTime=[],includeMetadata=True, verbose=True):
        """ Get Series list and  metadata

        Args:
           facility = 'CUTE', 'SLAC', 'NEXUS', etc.   (required)
           fridgeRun = 10, 11, etc or 'last' (required)
           seriesList = [231217_1200, 231224_1010,etc] (default: return all series if empty)
           isInSLAC = True/False (default: True, return only series at SLAC, based on nIsSLAC folder metadata)
           dataTypeList= [-1,0,1,2,..] (Default if emoty:  return all data types except test data -1)
           beginDateTime/endDateTime:  YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS
           includeMetadata = True/False (default: True). If True, return a dictionary, if False return a 
                             list of series numbe

        Output: dictionary or list
        """

        output_dict = dict()
        output_list = list() # if not metadata included, just list of series

        # =====================
        # Check arguments 
        # ===================== 
        if not facility or not fridgeRun:
            print('Required arguments: "facility" and "fridgeRun"')
            return
     
            
        if dataTypeList and not isInSLAC:
            print('ERROR: DataType can only be check if data in SLAC, please set "isInSLAC=True"!')
            return

        if beginDateTime:
            beginDateTime = str(beginDateTime)
            if (len(beginDateTime)!=6 and len(beginDateTime)!=11 and len(beginDateTime)!=13):
                print('ERROR: Format of beginDateTime available: YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS')
           
        if endDateTime:
            endDateTime = str(endDateTime)
            if (len(endDateTime)!=6 and len(endDateTime)!=11 and len(endDateTime)!=13):
                print('ERROR: Format of endDateTime available: YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS')
           
                
        if dataTypeList and type(dataTypeList)!=list:
            dataTypeList = [dataTypeList]

        if seriesList and type(seriesList)!=list:
            seriesList = [seriesList]

        # =====================
        # Get Series folders
        # from data catalog
        # =====================
        
              
        # fridge run
        run_name = str(fridgeRun)
        if run_name=='last':
            run_number = self.getLastFridgeRunNumber(facility)
            if run_number == -999999:
                print('ERROR: unable to find last fridge run number!')
                return
            run_name = 'R' + str(run_number)
            if verbose:
                print('Last Run: ' + run_name)
        elif run_name[0]!='R':
            run_name = 'R' + str(fridgeRun)
                              
        # list of series
        datacatalog_path = '/CDMS/' + facility+ '/' + run_name + '/Raw'
        folder_list = list()
        try:
            folder_list  = self.client.children(datacatalog_path)
        except:
            print('ERROR: Problem reading datacatalog path: ' +  datacatalog_path)
            return

       
        
        # ====================
        # Loop and Filter 
        # ====================
        for datacat_folder in folder_list:
            
            # series name and metadata
            series = datacat_folder.name
            series_metadata = dict()
            if (hasattr(datacat_folder,'metadata')):
                series_metadata= dict(datacat_folder.metadata)

            # check series name
            if (len(series) != 13 and len(series) != 15):
                continue    
        
            # check facility
            facility_id  = int(series[0:2])
            facility_name = self.getFacilityName(facility_id)
            if (facility_name != facility):
                continue
        
            # check if in series list
            if seriesList:
                if series not in seriesList:
                    continue
        
            # check in SLAC
            if isInSLAC:
                if (('nIsInSLAC' not in series_metadata)
                    or  ('nIsInSLAC' in series_metadata and 
                         int(series_metadata['nIsInSLAC'])==0)): 
                    continue


            # check data type
            if dataTypeList and type(dataTypeList)!=list:
                data_type = int(series_metadata['nDataType'])
                if data_type not in dataTypeList:
                    continue

            # check date range
            if beginDateTime or endDateTime:

                # remove underscore and facility id
                pos_underscore = series.find('_')
                series_time = series[pos_underscore-6:]
                series_time =  series_time.replace('_','')
                if len(series_time)==10:
                    series_time += '00'
                    
                # begin date
                if beginDateTime:
                    start = beginDateTime.replace('_','')
                    if len(start) < 12:
                        for ii in range(0,12-len(start)):
                            start+='0'
                    if (len(start) != len(series_time)):
                        print('\nWARNING: Format of "beginDateTime" not understood...')
                        print('It should be YYMMDD, YYMMDD_HHMM or YYMMDD_HHMMSS')
                        return output_dict
                    if int(series_time)<int(start):
                        continue


                # end date
                if endDateTime:
                    end = endDateTime.replace('_','')
                    if len(end) < 12:
                        for ii in range(0,12-len(end)):
                            end+='0'
                    if (len(end) != len(series_time)):
                        print('\nWARNING: Format of "endDateTime" not understood...') 
                        print('It should be YYMMDD, YYMMDD_HHMM or YYMMDD_HHMMSS')
                        return output_dict
                    if int(series_time)>int(end):
                        continue
                
            # output
            if includeMetadata:
                output_dict[series] = series_metadata
            else:
                output_list.append(series)
    
        if includeMetadata:
            return output_dict
        else:
            return output_list

    


    def getRawDataList(self,facility='',fridgeRun='', location = 'SLAC', seriesList=[], 
                       dataTypeList=[], beginDateTime=[],endDateTime=[], verbose=True):
        """ Get raw data file list

        Args:
           facility = 'CUTE', 'SLAC', 'NEXUS', etc.   (required) 
           fridgeRun = 'last OR 10, 11, etc   (required)
           location = 'SLAC','SNOLAB', etc. [default: data files located at 'SLAC')
           seriesList = [231217_1200, 231224_1010,etc] (default: return all series if empty)
           dataTypeList= [-1,0,1,2,..] (Default if empty:  return all data types except test data -1)
           beginDateTime/endDateTime:  YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS
           
        Output: dictionary 
        """

        # initialize output
        output_dict  = dict()

        # ======================
        # Check Input arguments
        # ======================
        if not facility or not fridgeRun:
            print('Required arguments: "facility" and "fridgeRun"')
            return
        
      
        # fridge run
        run_name = str(fridgeRun)
        if run_name=='last':
            run_number = self.getLastFridgeRunNumber(facility)
            if run_number == -999999:
                print('ERROR: unable to find last fridge run number!')
                return
            run_name = 'R' + str(run_number)
        elif run_name[0]!='R':
            run_name = 'R' + str(fridgeRun)
            
        
        if dataTypeList and type(dataTypeList)!=list:
            dataTypeList = [dataTypeList]

        if seriesList and type(seriesList)!=list:
            seriesList = [seriesList]
            
        # get list of series

        # if location is SLAC, then filter based on folder metadata
        isInSLAC = True
        if location!='SLAC':
            isInSLAC = False 
            
        # ======================
        # Get list of series
        # ======================
        
        series_list = self.getSeriesInfo(facility=facility,fridgeRun=fridgeRun,
                                         seriesList=seriesList, isInSLAC=isInSLAC, 
                                         dataTypeList=dataTypeList, 
                                         beginDateTime=beginDateTime,endDateTime=endDateTime,
                                         includeMetadata=False)
        
        if not series_list:
            print('WARNING: No series found! Check arguments')
            return

        print('Will search the file list for ' + str(len(series_list)) + ' series!')
        print('Be patient! It may take a while...')
    
        
        # ======================
        # Get files
        # ======================

        # loop and get files 
        for series in series_list:
        
            # get files
            datacatalog_path =  '/CDMS/' + facility +'/' + run_name + '/Raw/' + series
            raw_datasets = []
        
            try:
                raw_datasets = self.client.children(datacatalog_path,site=location)
            except:
                continue
            
            if not raw_datasets:
                continue
            
            file_list = []
            for dataset in  raw_datasets:
                file_list.append(dataset.resource)

            output_dict[series] = file_list
            


                            
        return output_dict



    def getProcessedDataList(self,facility='',fridgeRun='', productionTag='',fileType = '', 
                             location = 'SLAC', seriesList=[], dataTypeList=[], 
                             beginDateTime='',endDateTime='',outputSeriesDictFormat=False, 
                             verbose=True):
        """ Get processed data file list

        Args:
           facility = 'CUTE', 'SLAC', 'NEXUS', etc.   (required) 
           fridgeRun = 'last',or  10, 11, etc  (required)
           productionTag = production tag, example 'Prodv5.9.3', etc. (required) 
           fileType = 'unmerged', 'submerged','merged','noise' (default: 'submerged')
           location = 'SLAC','SNOLAB', etc. [default: data files located at 'SLAC')
           seriesList = [231217_1200, 231224_1010,etc] (default: return all series if empty)
           dataTypeList= [-1,0,1,2,..] (Default if empty:  return all data types except test data -1)
           beginDateTime/endDateTime:  YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS
           outputSeriesDictFormat = True/False (if True return a dictionart with key=Series number, value: list of files)
           
        Output: dictionary (if outputSeriesDictFormat=True)  or list (if outputSeriesDictFormat=False)
        """



        # initlize ouput
        output_dict  = dict() # outputSeriesDictFormat=True
        output_list  = list() # outputSeriesDictFormat=False


        # ======================
        # Check Input arguments
        # ======================
        if not facility or not fridgeRun or not productionTag:
            print('ERROR: Required arguments = "facility", "fridgeRun", and "productionTag"')
            if not productionTag:
                print('Use function "getProductionInfo" to get list of available tags!')
            return
             

        if not fileType:
            if verbose:
                print('No file type provided! Will use "submerged')
            fileType = 'Submerged'

        if dataTypeList and type(dataTypeList)!=list:
            dataTypeList = [dataTypeList]

        if seriesList and type(seriesList)!=list:
            seriesList = [seriesList]
        
        fileType = fileType[0].capitalize() + fileType[1:]
        if fileType!='Submerged' and  fileType!='Merged' and fileType!='Unmerged' and fileType!='Noise':
            print('ERROR: "fileType" argument should be "noise","merged", "submerged", or "unmerged"')
            return
        
        
        if beginDateTime:
            beginDateTime = str(beginDateTime)
            if (len(beginDateTime)!=6 and len(beginDateTime)!=11 and len(beginDateTime)!=13):
                print('ERROR: Format available for  "beginDateTime": YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS')
                return
            beginDateTime = beginDateTime.replace('_','')
            if len(beginDateTime) < 12:
                for ii in range(0,12-len(beginDateTime)):
                    beginDateTime+='0'
            
           
        if endDateTime:
            endDateTime = str(endDateTime)
            if (len(endDateTime)!=6 and len(endDateTime)!=11 and len(endDateTime)!=13):
                print('ERROR: Format available for "endDateTime": YYMMDD, YYMMDD_HHMM, YYMMDD_HHMMSS')
                return
            endDateTime = endDateTime.replace('_','')
            if len(endDateTime) < 12:
                for ii in range(0,12-len(endDateTime)):
                    endDateTime+='0'


        # get fridge run
        run_name = str(fridgeRun)
        if run_name=='last':
            run_number = self.getLastFridgeRunNumber(facility)
            if run_number == -999999:
                print('ERROR: unable to find last fridge run number!')
                return
            run_name = 'R' + str(run_number)
            if verbose:
                print('Last Run: ' + run_name)
        elif run_name[0]!='R':
            run_name = 'R' + str(fridgeRun)
            

        # check if release or tests
        base_path = '/CDMS/' + facility + '/' + run_name + '/Processed'
        productionType = str()
        try:
            if self.exist(base_path +'/Releases/' + productionTag):
                productionType = 'Releases'
            elif self.exist(base_path +'/Tests/' + productionTag):
                productionType = 'Tests'
        except:
            print('ERROR: Problem accessing data catalog!')
            return

        if not  productionType:
            print('ERROR: No data with tag "' + productionTag + '" found in the datacatalog!')
            print('Use function "getProductionInfo" to get list of available tags.')
            return


        if seriesList and not isinstance(seriesList,list):
            seriesList = [seriesList]

        if dataTypeList and not isinstance(dataTypeList,list):
            dataTypeList = [dataTypeList]
            
        # ======================
        # Get datasets
        # ======================
       
        # full path
        base_path += '/' + productionType + '/' + productionTag + '/' + fileType
        if fileType=='Unmerged':
            base_path += '/*'


        # build filter string
        query = 'nIsJunk==0' 
        if seriesList:
            query += ' and (Series=="{}"'.format(seriesList[0])
            for series in seriesList[1:]:
                query+= ' or Series=="{}"'.format(series)
            query+= ')'
        if dataTypeList:
            query+=' and (nDataType=='+str(dataTypeList[0])
            for data_type in dataTypeList[1:]:
                query+=' or nDataType=='+str(data_type)
            query+= ')'   
        if beginDateTime:
            query+=' and nSeriesDateTime>='+str(beginDateTime)
        if endDateTime:
            query+=' and nSeriesDateTime<='+str(endDateTime)

        show = ['Series']
        dataset_list = []
        try:
            dataset_list =  self.search(base_path,site=location,query=query,show=show)
        except:
            print('ERROR: Problem accessing data catalog!')
            print('Perhaps the files were produced prior January 2020 and do not have the proper metadata?')
            return

        if not dataset_list:
            print('WARNING: No processed file found for "'+productionTag+'". Check data catalog!')
            return 

        # loop datasets
        for dataset in dataset_list:
            series = dataset.metadata['Series']
            file_name = dataset.filePath 
            if outputSeriesDictFormat:
                if series not in output_dict:
                    output_dict[series] = []
                output_dict[series].append(file_name)
            else:
                output_list.append(file_name)
                                
        if outputSeriesDictFormat:
            return output_dict
        else:
            return output_list



    def getFacilityName(self,facility_id):  
            
        facility = str()

        # list of facilities
        facilities_dict= {1:'Soudan',2:'UCB',3:'CWRU',4:'UFL',5:'TAMU',6:'Queens',
                          7:'UMN',8:'Denver',9:'SLAC',
                          21:'TRIUMF',22:'FNAL',23:'CUTE',24:'SNOLAB',25:'NEXUS',26:'TUNL',
                          51:'DMC',99:'DAQTesting'}  

        if facility_id in facilities_dict:
            facility = facilities_dict[facility_id]

        return facility

        
    def getLastFridgeRunNumber(self, facility='CUTE'):

        last_run = -999999
        
        # base path
        base_path = '/CDMS/' + facility

        # run list
        folder_list = list()
        try:
            folder_list = self.client.children(base_path)
        except:
            print(f'ERROR: Unable to read datacatalog path "{base_path}"!')
            return last_run
        
        if not folder_list:
            print(f'ERROR: No fridge run found in {datacat_path}')
            return last_run

        for datacat_folder in folder_list:
            run = datacat_folder.name
            try:
                last_run = max(last_run, int(run[1:]))
            except ValueError: #run is not a number?
                pass

        return last_run
        
