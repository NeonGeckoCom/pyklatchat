from enum import Enum


class MigrationFiles(Enum):
    """Enum containing migration files"""

    NICK_MAPPING = 'nick_mapping.json'
    CIDS = 'cids.txt'
