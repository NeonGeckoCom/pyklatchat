from abc import ABC, abstractmethod
from typing import Optional
from enum import Enum


class DatabaseTypes(Enum):
    RELATIONAL = 1
    NOSQL = 2


class DatabaseConnector(ABC):
    """Base class for database"""

    @abstractmethod
    def __init__(self, config_data: dict):
        self.config_data = config_data
        self._cnx = None

    @abstractmethod
    @property
    def database_type(self) -> DatabaseTypes:
        pass

    @property
    def connection(self):
        return self._cnx

    @abstractmethod
    def create_connection(self):
        """Creates new database connection"""
        pass

    @abstractmethod
    def abort_connection(self):
        """Aborts existing connection"""
        pass

    @abstractmethod
    def exec_raw_query(self, query_str: str, *args) -> Optional[list]:
        """
            Executes raw query returns result if needed
            :param query_str: query string to execute
            :param args: query args (if needed)
        """
        pass
