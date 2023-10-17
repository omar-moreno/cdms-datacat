import subprocess
import pkg_resources
from .CDMSDataCatalog import CDMSDataCatalog
from .CDMSDataset import ParticleHits, DMCintermediate, RawSim, ProcessedSim

def build_dataset_from_metadata(filePath, dict_metadata):
    input_ds = {'filename': filePath.split('/')[-1], 'filePath': filePath}
    for k in dict_metadata.keys():
        input_ds[k] = dict_metadata[k]

    dataset = None
    if 'SimStage' in dict_metadata.keys():
        input_ds.pop('SimStage')
        if   dict_metadata['SimStage'] == 'SourceSim': dataset = ParticleHits(   **input_ds)
        elif dict_metadata['SimStage'] == 'DMC'      : dataset = DMCintermediate(**input_ds)
        elif dict_metadata['SimStage'] == 'DAQSim'   : dataset = RawSim(         **input_ds)
        elif dict_metadata['SimStage'] == 'Processed': dataset = ProcessedSim(   **input_ds)

    if dataset:
        if dataset.check_conventions():
            return dataset
    print('ERROR: unable to build valid dataset')
    return None

def get_dc_path(dict_metadata):
    dataset = build_dataset_from_metadata('', dict_metadata) # First argument (filePath) is not necessary because dataset will not be registered

    if dataset:
        return dataset.relativePath
    return None

def register(filePath, dict_metadata, dry_run = False):
    dc_default = CDMSDataCatalog(pkg_resources.resource_filename(__name__, 'cfg/default.cfg'))
    dc_prod    = CDMSDataCatalog(pkg_resources.resource_filename(__name__, 'cfg/prod.cfg'   ))

    dataset = build_dataset_from_metadata(filePath, dict_metadata)

    if dataset:
        ancestor = None
        if dataset.Ancestorpath:
            ancestors = dataset.get_ancestors(dc_default)
            if not ancestors:
                print('ERROR: unable to find ancestors')
                return False
            if len(ancestors) == 1:
                ancestor = ancestors[0]
            else:
                print('ERROR: multiple ancestors found')
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
            if ancestor:
                dataset = dc_default.get(dataset.relativePath+'/'+dataset.datasetName)
                dc_prod.addDependents(dataset, 'predecessor', dep_datasets = [dc_default.get(ancestor.relativePath)])
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

def transfer_ssh(filePaths, list_dict_metadata, user, remote, basedir):
    path_local = None
    relativePath = None

    for i in range(len(filePaths)):
        if type(path_local) == str:
            if '/'.join(filePaths[i].split('/')[:-1]) != path_local:
                print('Error: all files must be in the same local directory')
                return False
        else:
            path_local = '/'.join(filePaths[i].split('/')[:-1])

        if type(relativePath) == str:
            if get_dc_path(list_dict_metadata[i]) != relativePath:
                print('Error: all files must be registered in the same Data Catalog folder')
                return False
        else:
            relativePath = get_dc_path(list_dict_metadata[i])

    path_remote = basedir+relativePath
    if not path_remote[-1] == '/':
        path_remote += '/'
    print('Transferring files from', path_local+'/', 'to', remote+':'+path_remote)
    subprocess.run('rsync -a --no-p --rsync-path="mkdir -p '+path_remote+' && rsync" '+path_local+' '+user+'@'+remote+':'+path_remote, shell = True)
    return True

def transfer_globus(filePaths, list_dict_metadata, client_id, source_endpoint_id, dest_endpoint_id, basedir):
    # slac#osg: endpoint_id = 'd98c7f90-6d04-11e5-ba46-22000b92c6ec'
    # slac#sdf: endpoint_id = 'dda770be-f428-11eb-ab64-d195c983855c'
    # slac#s3df: endpoint_id = '649de2a6-8a58-11e5-9967-22000b96db58'
    # Elias Lopez Asamar - Laptop UAM: endpoint_id = 'f9c2873c-411c-11ee-b696-812118bf21b5'

    import globus_sdk
    from globus_sdk.scopes import TransferScopes

    auth_client = globus_sdk.NativeAppAuthClient(client_id)
    auth_client.oauth2_start_flow(requested_scopes = TransferScopes.all) # Only request access to the Transfer API
    auth_code = input('Please go to '+auth_client.oauth2_get_authorize_url()+', and enter here the code provided upon login: ').strip()
    tokens = auth_client.oauth2_exchange_code_for_tokens(auth_code)
    transfer_tokens = tokens.by_resource_server['transfer.api.globus.org']

    transfer_client = globus_sdk.TransferClient(authorizer = globus_sdk.AccessTokenAuthorizer(transfer_tokens['access_token']))
    out_activation = transfer_client.endpoint_autoactivate(dest_endpoint_id, if_expires_in = 3600)
    while out_activation['code'] == 'AutoActivationFailed':
        input('Please go to https://app.globus.org/file-manager?origin_id='+dest_endpoint_id+', and press ENTER upon login')
        out_activation = transfer_client.endpoint_autoactivate(dest_endpoint_id, if_expires_in = 3600)
    task_data = globus_sdk.TransferData(source_endpoint = source_endpoint_id, destination_endpoint = dest_endpoint_id)

    for i in range(len(filePaths)):
        relativePath = get_dc_path(list_dict_metadata[i])
        if not relativePath:
            print('Warning: file', filePaths[i], 'will not be transferred (unable to determine Data Catalog path)')
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

    task_doc = transfer_client.submit_transfer(task_data)
    print('Transfer submitted with task_id =', task_doc['task_id'])
    return True

def build_dict_metadata_swft(site, fileFormat, filePath_metadata_dataset, filePath_metadata_folder):
    dict_metadata = {'site': site, 'fileFormat': fileFormat}
    f = open(filePath_metadata_dataset)
    for l in f.readlines():
        lparts = l.split('"')
        if len(lparts) == 3:
            dict_metadata[lparts[1]] = str(int(lparts[2][2:]))
        elif len(lparts) == 5:
            if lparts[1] == 'ProdTag':
                continue
            dict_metadata[lparts[1]] = lparts[3]
    f.close()
    f = open(filePath_metadata_folder)
    for l in f.readlines():
        lparts = l.split('"')
        if len(lparts) == 3:
            if lparts[1] == 'nEvAll': # This statement should be removed if this field is eventually removed from the folder metadata
                continue
            dict_metadata[lparts[1]] = str(int(lparts[2][2:]))
        elif len(lparts) == 5:
            if lparts[1] == 'ProdTag':
                continue
            if not lparts[1] in dict_metadata.keys():
                dict_metadata[lparts[1]] = lparts[3]
    f.close()
    if (dict_metadata['SimStage'] == 'SourceSim' or dict_metadata['SimStage'] == 'DMC') and 'Series' in dict_metadata.keys(): # This statement might not be necessary in the future
        dict_metadata.pop('Series')
    return dict_metadata
