def corrPathCDMS(path):
    if path[0] != "/":
        path = "/" + path

    if path[1:5] != "CDMS":
        path = "/CDMS" + path

    return path


def debug_add(dc, CDMSds, replace=True, catch_errors=True):
    if CDMSds.dataType == "DatacatQuery":
        raise ValueError('Cannot commit dataset with type "DatacatQuery", invalid type')
    path = corrPathCDMS(CDMSds.relativePath)
    DSexists = dc.client.exists(path + "/" + CDMSds.datasetName)
    if DSexists:
        if replace:
            print("Replacing existing dataset:", path, "/", CDMSds.datasetName)
        else:
            print("Skipping existing dataset:", path, "/", CDMSds.datasetName)

    if not DSexists or replace:
        print("## Positional arguments to mkds")
        print((path, CDMSds.datasetName, CDMSds.fileType, CDMSds.fileFormat))
        print("## Keyword arguments to mkds")
        print(
            dict(
                versionMetadata=CDMSds.metadata,
                resource=CDMSds.filePath,
                site=CDMSds.site,
            )
        )
