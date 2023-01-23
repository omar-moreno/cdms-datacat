""" Provides the CDMSGroup class"""

from datacat.model import Metadata


class CDMSGroup:
    """Class for CDMS group

       Attributes:
    """

    def __init__(self,
                 name,
                 path):
        """ ##Constructor
                All arguments are mandatory.
                Args:
                    name (str): Name of the group entry.
                    path(str): Full absolute path to the group
               """
        self.name = name
        self.path = path
        self.metadata = Metadata()

    @classmethod
    def fromGroup(cls, group):
        """ Construct a `CDMSGroup` from a raw `datacat.model.Group`
            Args:
                group (Group): the datacat.model.Group object
        """
        ngroup = cls(str(group.name), str(group.path))
        # copy metadata
        for k, v in getattr(group, 'metadata', {}).items():
            ngroup.metadata[k] = v
        ngroup.rawGroup = group
        return ngroup
