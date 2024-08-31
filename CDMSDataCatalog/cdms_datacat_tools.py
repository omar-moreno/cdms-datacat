import sys
sys.dont_write_bytecode = True
import subprocess
import pkg_resources
from .CDMSDataCatalog import CDMSDataCatalog
from .CDMSDataset import *

def build_dataset_from_metadata(filePath, dict_metadata):
    input_ds = {'filename': filePath.split('/')[-1], 'filePath': filePath}
    for k in dict_metadata.keys():
        input_ds[k] = dict_metadata[k]

    dataset = None
    if 'SimStage' in dict_metadata.keys():
        input_ds.pop('SimStage')
        if dict_metadata['SimStage'] == 'SourceSim':
            dataset = ParticleHits(**input_ds)
        elif dict_metadata['SimStage'] == 'DMC':
            dataset = DMCintermediate(**input_ds)
        elif dict_metadata['SimStage'] == 'DAQSim':
            dataset = RawSim(**input_ds)
        elif dict_metadata['SimStage'] == 'Processed':
            if 'ProdStep' in dict_metadata.keys():
                if dict_metadata['ProdStep'] == 'BatNoise':
                    dataset = NoiseSim(**input_ds)
                elif 'nMergeLevel' in dict_metadata.keys():
                    if dict_metadata['nMergeLevel'] == 0:
                        dataset = UnmergedSim(**input_ds)
                    elif dict_metadata['nMergeLevel'] == 1:
                        dataset = SubmergedSim(**input_ds)
                    elif dict_metadata['nMergeLevel'] == 2: # For consistency with the actual processed data
                        dataset = MergedSim(**input_ds)

    if dataset:
        if dataset.check_conventions():
            return dataset
    print('ERROR: unable to build valid dataset')
    return None

def get_dc_path(filePath, dict_metadata, include_last_dir = False, test_folder = False):
    dataset = build_dataset_from_metadata(filePath, dict_metadata)

    if dataset:
        if include_last_dir:
            dataset.include_last_dir()
        if test_folder: # To be removed after DC3...
            dataset.enable_test_folder()
        return dataset.relativePath
    return None

def register(filePath, dict_metadata, include_last_dir = False, dry_run = False, test_folder = False):
    dc_default = CDMSDataCatalog(pkg_resources.resource_filename(__name__, 'cfg/default.cfg'))
    dc_prod    = CDMSDataCatalog(pkg_resources.resource_filename(__name__, 'cfg/prod.cfg'   ))

    dataset = build_dataset_from_metadata(filePath, dict_metadata)

    if dataset:
        if include_last_dir:
            dataset.include_last_dir()
        if test_folder: # To be removed after DC3...
            dataset.enable_test_folder()

        ancestors = None
        if dataset.Ancestorpath:
            ancestors = dataset.get_ancestors(dc_default)
            for ancestor in ancestors:
                if not ancestor:
                    print('ERROR: unable to find ancestors')
                    return False
                elif len(ancestor) > 1:
                    print('ERROR: ancestor search provides ambiguous results')
                    return False

        if not dc_default.exist(dataset.relativePath): # Checking whether folder already exists
            if dry_run:
                print('INFO: dry-run, folder not created')
            else:
                dc_prod.mkdir(dataset.relativePath, parents = True, metadata = dataset.metadata_folder) # If not, create folder automatically
        # else: check that folder metadata are consistent!

        if dry_run:
            print('INFO: dry-run, dataset not registered')
        else:
            dc_prod.add(dataset)
            if ancestors:
                dataset = dc_default.get(dataset.relativePath+'/'+dataset.datasetName)
                dc_prod.addDependents(dataset, 'predecessor', dep_datasets = [dc_default.get(ancestor[0].relativePath) for ancestor in ancestors])
        return True

    return False

def search(path, site = 'All', dofetch = False, fetchargs = {}, **kwargs): # For now this is just a placeholder
    """
    kwargs are only used by search, not fetch
    fetch kwargs are provided by fetchargs
    """
    config = pkg_resources.resource_filename(__name__, 'cfg/default.cfg')
    dc = CDMSDataCatalog(config)
    datasets = dc.search(path, site = site, **kwargs)
    if dofetch:
        datasets = self.fetch(datasets, **fetchargs)
    return datasets

def find_nDump_from_nTriggerId(Series, nTriggerId, Facility, nFridgeRun = None, site = 'All'):
    relativePath = '/CDMS/'+Facility
    if type(nFridgeRun) == int:
        relativePath += '/R'+str(nFridgeRun)
    config = pkg_resources.resource_filename(__name__, 'cfg/default.cfg')
    dc = CDMSDataCatalog(config)
    datasets = dc.search(relativePath+'/**', site = site, query = 'Series eq "'+Series+'" and nFirstTriggerId lteq '+str(nTriggerId)+' and nLastTriggerId gteq '+str(nTriggerId))
    if len(datasets) == 1:
        return dc.get(datasets[0].relativePath).metadata['nDump'] 
    if len(datasets) == 0:
        print('ERROR: no files found for Series = '+Series+' and nTriggerId = '+str(nTriggerId))
    else:
        print('ERROR: multiple files found for Series = '+Series+' and nTriggerId = '+str(nTriggerId))
    return None

def transfer_ssh(filePaths, list_dict_metadata, user, remote, basedir, include_last_dir = False, test_folder = False):
    path_local = None
    relativePath = None

    for i in range(len(filePaths)):
        if type(path_local) == str:
            if '/'.join(filePaths[i].split('/')[:-1]) != path_local:
                print('ERROR: all files must be in the same local directory')
                return None
        else:
            path_local = '/'.join(filePaths[i].split('/')[:-1])

        if type(relativePath) == str:
            if get_dc_path(filePaths[i], list_dict_metadata[i], include_last_dir, test_folder) != relativePath:
                print('ERROR: all files must be registered in the same Data Catalog folder')
                return None
        else:
            relativePath = get_dc_path(filePaths[i], list_dict_metadata[i], include_last_dir, test_folder)

    path_remote = (basedir+relativePath).replace('//', '/')
    if not path_remote[-1] == '/':
        path_remote += '/'
    print('Transferring files from', path_local+'/', 'to', remote+':'+path_remote)
    subprocess.run('rsync -a --no-p --rsync-path="mkdir -p '+path_remote+' && rsync" '+path_local+'/* '+user+'@'+remote+':'+path_remote, shell = True)
    return [path_remote+filePaths[i].split('/')[-1] for i in range(len(filePaths))]


def get_access_token_globus(client_id, arg_consent=None):
    import globus_sdk
    from globus_sdk.scopes import TransferScopes, GCSCollectionScopeBuilder

    auth_client = globus_sdk.NativeAppAuthClient(client_id)
    scope = globus_sdk.Scope(TransferScopes.all)

    if arg_consent:
        for collection_id in arg_consent.split():
            print(f"\nProcessing collection ID: {collection_id}")
            try:
                # Build the data_access scope for the given collection ID
                # (data_access scopes are specific to non-High-Assurance Mapped Collections.)
                collection_scope = GCSCollectionScopeBuilder(collection_id).data_access
                scope.add_dependency(collection_scope, optional=True)
            except Exception as e:
                print("\nThe data_access scopes are specific to non-High-Assurance Mapped Collections. They are not created for any other collection type (Guest Collection, High-Assurance Mapped Collection).")
                print(f"Error processing scope for collection {collection_id}: {e}")

    print(f"\nFinal requested scope: {scope}\n")
    auth_client.oauth2_start_flow(requested_scopes=scope)
    auth_code = input('Please go to '+auth_client.oauth2_get_authorize_url()+', and enter here the code provided upon login: ').strip()
    tokens = auth_client.oauth2_exchange_code_for_tokens(auth_code)
    transfer_tokens = tokens.by_resource_server['transfer.api.globus.org']
    return transfer_tokens['access_token']


def transfer_globus(filePaths, list_dict_metadata, access_token, source_endpoint_id, dest_endpoint_id, basedir, include_last_dir = False, test_folder = False):
    # slac#s3df_globus5: endpoint_id = '31f8393f-79ef-4da4-a395-7127edd9b3a4'
    # Elias Lopez Asamar - Laptop UAM: endpoint_id = 'f9c2873c-411c-11ee-b696-812118bf21b5'

    import globus_sdk

    transfer_client = globus_sdk.TransferClient(authorizer = globus_sdk.AccessTokenAuthorizer(access_token))
    out_activation = transfer_client.endpoint_autoactivate(dest_endpoint_id, if_expires_in = 3600)
    while out_activation['code'] == 'AutoActivationFailed':
        input('Please go to https://app.globus.org/file-manager?origin_id='+dest_endpoint_id+', and press ENTER upon login')
        out_activation = transfer_client.endpoint_autoactivate(dest_endpoint_id, if_expires_in = 3600)
    task_data = globus_sdk.TransferData(transfer_client = transfer_client, source_endpoint = source_endpoint_id, destination_endpoint = dest_endpoint_id)

    filePaths_remote = []
    for i in range(len(filePaths)):
        relativePath = get_dc_path(filePaths[i], list_dict_metadata[i], include_last_dir, test_folder)
        if not relativePath:
            print('WARNING: file', filePaths[i], 'will not be transferred (unable to determine Data Catalog path)')
            continue

        # Creating the directory structure given by relativePath, if necessary
        # Could not find a better method to do this...
        absolutePath = basedir[:-1] if basedir[-1] == '/' else basedir
        for dirname in relativePath.split('/')[1:]:
            for entry in transfer_client.operation_ls(dest_endpoint_id, absolutePath):
                if entry['name'] == dirname and entry['type'] == 'dir':
                    break
            else:
                print('Creating directory '+dest_endpoint_id+':'+absolutePath+'/'+dirname)
                transfer_client.operation_mkdir(dest_endpoint_id, absolutePath+'/'+dirname)
            absolutePath += '/'+dirname

        filePath_remote = absolutePath+'/'+filePaths[i].split('/')[-1]
        task_data.add_item(filePaths[i], filePath_remote)
        print('Adding transfer from', source_endpoint_id+':'+filePaths[i], 'to', dest_endpoint_id+':'+filePath_remote)
        filePaths_remote.append(filePath_remote)

    task_doc = transfer_client.submit_transfer(task_data)
    print('Transfer submitted with task_id =', task_doc['task_id'])
    return filePaths_remote

def build_dict_metadata_swft(site, fileFormat, filePath_metadata_dataset, filePath_metadata_folder):
    import ast

    dict_metadata = {'site': site, 'fileFormat': fileFormat}
    f = open(filePath_metadata_dataset)
    dict_from_f = ast.literal_eval(''.join(f.readlines()).split('=')[-1])
    for k in dict_from_f.keys():
        if k == 'ProdTag':
            continue
        if k == 'AncestorPath':
            dict_metadata['Ancestorpath'] = dict_from_f[k]
        elif type(dict_from_f[k]) == int and not (k[0] == 'n' and k[1].isupper()):
            dict_metadata[k] = str(dict_from_f[k])
        else:
            dict_metadata[k] = dict_from_f[k]
    f.close()
    f = open(filePath_metadata_folder)
    dict_from_f = ast.literal_eval(''.join(f.readlines()).split('=')[-1])
    for k in dict_from_f.keys():
        if k == 'nEvAll' or k == 'ProdTag': # This statement should be modified if nEvAll is eventually removed from the folder metadata
            continue
        if type(dict_from_f[k]) == int and not (k[0] == 'n' and k[1].isupper()):
            if k in dict_metadata.keys():
                if str(dict_from_f[k]) != dict_metadata[k]:
                    print('ERROR: conflict between dataset and folder metadata: '+k)
                    return None
            dict_metadata[k] = str(dict_from_f[k])
        else:
            if k in dict_metadata.keys():
                if dict_from_f[k] != dict_metadata[k]:
                    print('ERROR: conflict between dataset and folder metadata: '+k)
                    return None
            dict_metadata[k] = dict_from_f[k]
    f.close()
    if (dict_metadata['SimStage'] == 'SourceSim' or dict_metadata['SimStage'] == 'DMC') and 'Series' in dict_metadata.keys(): # This statement might not be necessary in the future
        dict_metadata.pop('Series')
    return dict_metadata

def create_group(groupname):
    dc_default = CDMSDataCatalog(pkg_resources.resource_filename(__name__, 'cfg/default.cfg'))
    dc_prod    = CDMSDataCatalog(pkg_resources.resource_filename(__name__, 'cfg/prod.cfg'   ))

    relativePath = groupname.rstrip('/') if groupname.find('/CDMS/')  == 0 else '/CDMS/'+groupname.strip('/') # Not enforcing any conventions on relativePath

    if not dc_default.exist(relativePath):
        dc_prod.mkgroup(relativePath, parents = True) # Not attaching any metadata to group
        return True
    else:
        print('WARNING: group '+groupname+' already exists')
    return False

def add_files_to_group(groupname, filePaths):
    dc = CDMSDataCatalog(pkg_resources.resource_filename(__name__, 'cfg/prod.cfg'   ))

    relativePath = groupname.rstrip('/') if groupname.find('/CDMS/')  == 0 else '/CDMS/'+groupname.strip('/')
    group = dc.getgroup(relativePath)

    datasets = []
    for filePath in filePaths:
        try:
            if filePath.find('/CDMS/') == 0: # Case 1: filePath is Data Catalog path
                datasets.append(dc.get(filePath))
            elif filePath.count('/CDMS/') == 1: # Case 2: filePath is actual path on disk, requires single occurrence of '/CDMS/'
                datasets.append(dc.get('/CDMS/'+filePath.split('/CDMS/')))
        except:
            print('ERROR: cannot find Data Catalog entry for file '+filePath)
            return False

    dc.addDependents(group, 'cdmsgroup', dep_datasets = datasets)
    return True

def retrieve_files_from_group(groupname, num_datasets = 1000000000):
    dc = CDMSDataCatalog(pkg_resources.resource_filename(__name__, 'cfg/default.cfg'))

    relativePath = groupname.rstrip('/') if groupname.find('/CDMS/')  == 0 else '/CDMS/'+groupname.strip('/')
    group = dc.getgroup(relativePath)
    return dc.getDependents(group, 'cdmsgroup', 1, num_datasets)
