from enum import Enum


class DataSources(Enum):
    """ Enumeration of supported data sources """
    SFTP = 'SFTP'
    LOCAL = 'LOCAL'
