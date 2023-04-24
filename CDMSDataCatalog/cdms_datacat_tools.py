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
        if   dict_metadata['SimStage'] == 'ParticleHits'   : dataset = ParticleHits(   **input_ds)
        elif dict_metadata['SimStage'] == 'DMCintermediate': dataset = DMCintermediate(**input_ds)
        elif dict_metadata['SimStage'] == 'Raw'            : dataset = RawSim(         **input_ds)
        elif dict_metadata['SimStage'] == 'Processed'      : dataset = ProcessedSim(   **input_ds)

    if dataset:
        if dataset.check_conventions():
            return dataset
    print('ERROR: unable to build valid dataset')
    return None

def get_dc_path(dict_metadata):
    dataset = build_dataset_from_metadata('', dict_metadata) # First argument (filePath) is not necessary because dataset will not be registered

    if dataset:
        return dataset.get_dc_path()
    return None

def register(filePath, dict_metadata, dry_run = False):
    config = pkg_resources.resource_filename(__name__, 'cfg/prod.cfg')
    dc = CDMSDataCatalog(config)

    dataset = build_dataset_from_metadata(filePath, dict_metadata)

    if dataset:
        if dataset.Ancestorpath:
            if not dataset.link_to_ancestor(dc):
                print('ERROR: unable to link to ancestor')
                return False
        if not dc.exist(dataset.get_dc_path()): # Checking whether folder already exists
            dc.mkdir(dataset.get_dc_path(), parents = True, metadata = dataset.metadata_folder) # If not, create folder automatically
        # else: check that folder metadata are consistent!
        if dry_run:
            print('INFO: dry-run, dataset not registered')
        else:
            dc.add(dataset)
        
        return True

    return False

def search(path, site = 'All', dofetch = False, fetchargs = {}, **kwargs):
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
