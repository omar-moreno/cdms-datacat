def build_dict_metadata(site, fileFormat, fname_md_dataset, fname_md_folder):
    dict_metadata = {'site': site, 'fileFormat': fileFormat}
    f = open(fname_md_dataset)
    for l in f.readlines():
        lparts = l.split('"')
        if len(lparts) == 3:
            dict_metadata[lparts[1]] = str(int(lparts[2][2:]))
        elif len(lparts) == 5:
            if lparts[1] == 'ProdTag':
                continue
            dict_metadata[lparts[1]] = lparts[3]
    f.close()
    f = open(fname_md_folder)
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
    return dict_metadata
