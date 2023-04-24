import subprocess
from .cdms_datacat_tools import get_dc_path

def transfer(filePath, dict_metadata, user, remote, basedir):
    relativePath = get_dc_path(dict_metadata)
    if not relativePath:
        return False

    path_remote = basedir+relativePath
    print('Transferring file '+filePath+' to '+remote+':'+path_remote)
    subprocess.run('rsync -a --rsync-path="mkdir -p '+path_remote+' && rsync" '+filePath+' '+user+'@'+remote+':'+path_remote, shell = True)
    return True
