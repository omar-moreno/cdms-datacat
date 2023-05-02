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
