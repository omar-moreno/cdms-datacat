import subprocess
from .cdms_datacat_tools import get_dc_path

def transfer_ssh(filePath, dict_metadata, user, remote, basedir):
    relativePath = get_dc_path(dict_metadata)
    if not relativePath:
        return False

    path_remote = basedir+relativePath
    print('Transferring file '+filePath+' to '+remote+':'+path_remote)
    subprocess.run('rsync -a --rsync-path="mkdir -p '+path_remote+' && rsync" '+filePath+' '+user+'@'+remote+':'+path_remote, shell = True)
    return True

import globus_sdk
from globus_sdk.scopes import TransferScopes

class TransferManager_globus:
    
    def __init__(self):
        self.filePaths = []
        self.list_dict_metadata = []

    def add_dataset(self, filePath, dict_metadata):
        self.filePaths.append(filePath)
        self.list_dict_metadata.append(dict_metadata)

    def do_transfer(self, client_id, source_endpoint_id, dest_endpoint_id, basedir):
        # slac#osg: endpoint_id = 'd98c7f90-6d04-11e5-ba46-22000b92c6ec'
        # slac#sdf: endpoint_id = 'dda770be-f428-11eb-ab64-d195c983855c'
        # slac#s3df: endpoint_id = '649de2a6-8a58-11e5-9967-22000b96db58'
        # Elias Lopez Asamar - Laptop UAM: endpoint_id = 'f9c2873c-411c-11ee-b696-812118bf21b5'

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

        for i in range(len(self.filePaths)):
            relativePath = get_dc_path(self.list_dict_metadata[i])
            if not relativePath:
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

            filePath_remote = absolutePath+'/'+self.filePaths[i].split('/')[-1]
            task_data.add_item(self.filePaths[i], filePath_remote)
            print('Adding transfer from '+source_endpoint_id+':'+self.filePaths[i]+' to '+dest_endpoint_id+':'+filePath_remote)

        task_doc = transfer_client.submit_transfer(task_data)
        print('Transfer submitted with task_id =', task_doc['task_id'])
        return True
